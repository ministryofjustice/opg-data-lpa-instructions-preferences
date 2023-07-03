import numpy as np

from tesserocr import PyTessBaseAPI, PSM


def _convert_cv2_to_bytes(image: np.ndarray):
    image_bytes = image.tobytes()
    bpp = image.shape[2] if len(image.shape) == 3 else 1
    h, w = image.shape[0:2]
    bpl = bpp * w
    return image_bytes, w, h, bpp, bpl


def get_text_from_image_file(image_locations: list[str]) -> list:
    api_kwargs = {"psm": PSM.AUTO_OSD, "lang": "eng"}
    api = PyTessBaseAPI(**api_kwargs)

    list_of_text = []
    for image_location in image_locations:
        image = np.load(image_location)
        image_bytes = _convert_cv2_to_bytes(image)
        api.SetImageBytes(*image_bytes)
        api.Recognize()
        text = api.GetUTF8Text()

        list_of_text.append(text)

    return list_of_text