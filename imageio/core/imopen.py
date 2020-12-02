from numbers import Number
import re
import numpy as np

from .format import FormatManager, MODENAMES
from .request import Request, RETURN_BYTES

"""

Convenience wrappers are found in core/functions.py
"""


class imopen(object):
    def __init__(self, uri, *args, plugin=None, mode='legacy', **kwargs):
        self._uri = uri
        self._plugin = None if plugin is None else FormatManager()[plugin]

        # legacy support removed from v3.0.0
        self._legacy = True if mode == "legacy" else False

    def read(self, *, index=None, iio_mode='?', **kwargs):
        """
        Parses the given URI and creates a ndarray from it.

        .. deprecated:: 2.9.0
          `iio_mode='?'` will be replaced by `iio_mode=None` in imageio v3.0.0 .

        Parameters
        ----------
        index : {integer}
            If the URI contains a list of ndimages return the index-th
            image. If None, behavior depends on the used api::

                Legacy-style API: return the first element (index=0)
                New-style API: stack list into ndimage along the 0-th dimension
                    (equivalent to np.stack(imgs, axis=0))

        iio_mode : {'i', 'v', '?', None}
            Used to give the reader a hint on what the user expects (default "?"):
            "i" for an image, "v" for a volume, "?" for don't care,
            and "None" to use the new API.
        kwargs : ...
            Further keyword arguments are passed to the reader. See :func:`.help`
            to see what arguments are available for a particular format.
        """

        if self._legacy:
            if iio_mode is None:
                raise ValueError(
                    "mode=None is not supported"
                    " for legacy API calls."
                )
            mode = "r" + iio_mode
            index = 0 if index is None else index

            request = Request(self._uri, mode, **kwargs)

            plugin = self._plugin
            if plugin is None:
                plugin = FormatManager().search_read_format(request)

            if plugin is None:
                modename = MODENAMES.get(mode, mode)
                raise ValueError(
                    "Could not find a format to read the specified file"
                    " in %s mode" % modename
                )

            return plugin.get_reader(request).get_data(index)

        else:
            raise NotImplementedError

    def write(self, image, *, iio_mode='?', **kwargs):
        """
        Write an ndimage to the URI specified in path.

        If the URI points to a file on the current host and the file does not
        yet exist it will be created. If the file exists already, it will be
        appended if possible; otherwise, it will be replaced.

        Parameters
        ----------
        image : numpy.ndarray
            The ndimage or list of ndimages to write.
        iio_mode : {'i', 'I', 'v', 'V', '?', None}
            Used to give the reader a hint on what the user expects (default "?"):
            "i" for an image, "I" for multiple images, "v" for a volume,
            "V" for multiple volumes, "?" for don't care, and "None" to use the
            new API prior to imageio v3.0.0.
        kwargs : ...
            Further keyword arguments are passed to the writer. See :func:`.help`
            to see what arguments are available for a particular format.
        """

        if self._legacy:
            if iio_mode is None:
                raise ValueError(
                    "mode=None is not supported"
                    " for legacy API calls."
                )
            mode = "w" + iio_mode

            plugin = self._plugin
            uri = self._uri
            # Signal extension when returning as bytes, needed by e.g. ffmpeg
            if uri == RETURN_BYTES and isinstance(plugin, str):
                uri = RETURN_BYTES + "." + plugin.strip(". ")

            request = Request(uri, mode, **kwargs)
            if plugin is None:
                plugin = FormatManager().search_write_format(request)

            if plugin is None:
                modename = MODENAMES.get(mode, mode)
                raise ValueError(
                    "Could not find a format to write the specified file in %s mode" % modename
                )

            writer = plugin.get_writer(request)
            with writer:
                if iio_mode in "iv?":
                    writer.append_data(image)
                else:
                    written = None
                    for written, image in enumerate(image):
                        # Test image
                        imt = type(image)
                        image = np.asanyarray(image)
                        if not np.issubdtype(image.dtype, np.number):
                            raise ValueError(
                                "Image is not numeric, but {}.".format(imt.__name__))
                        elif iio_mode == "I":
                            if image.ndim == 2:
                                pass
                            elif image.ndim == 3 and image.shape[2] in [1, 3, 4]:
                                pass
                            else:
                                raise ValueError(
                                    "Image must be 2D " "(grayscale, RGB, or RGBA).")
                        else:  # iio_mode == "V"
                            if image.ndim == 3:
                                pass
                            elif image.ndim == 4 and image.shape[3] < 32:
                                pass  # How large can a tuple be?
                            else:
                                raise ValueError(
                                    "Image must be 3D, or 4D if each voxel is a tuple.")

                        # Add image
                        writer.append_data(image)

                    if written is None:
                        raise RuntimeError("Zero images were written.")

            return writer.request.get_result()
        else:
            raise NotImplementedError

    # this could also be __iter__
    def iter(self, *, iio_mode='?', **kwargs):
        """
        Iterate over a list of ndimages given by the URI

        .. deprecated:: 2.9.0
          `iio_mode='?'` will be replaced by `iio_mode=None` in imageio v3.0.0 .

        Parameters
        ----------
        iio_mode : {'I', 'V', '?', None}
            Used to give the reader a hint on what the user expects (default "?"):
            "I" for multiple images, "V" for multiple volumes, "?" for don't care,
            and "None" to use the new API.
        kwargs : ...
            Further keyword arguments are passed to the reader. See :func:`.help`
            to see what arguments are available for a particular format.
        """

        if self._legacy:
            if iio_mode is None:
                raise ValueError(
                    "mode=None is not supported"
                    " for legacy API calls."
                )
            mode = "r" + iio_mode
            request = Request(self._uri, mode, **kwargs)

            plugin = self._plugin
            if plugin is None:
                plugin = FormatManager().search_read_format(request)

            if plugin is None:
                modename = MODENAMES.get(mode, mode)
                raise ValueError(
                    "Could not find a format to read the specified file"
                    " in %s mode" % modename
                )

            for image in plugin.get_reader(request):
                yield image

        else:
            raise NotImplementedError

    def get_meta(self):
        raise NotImplementedError

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass
