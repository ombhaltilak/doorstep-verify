from typing import Optional
from pydantic import BaseModel


class VerifyRequest(BaseModel):
    tracking_id:  str
    barcode:      str
    gps:          dict
    driver_id:    str
    media_type:   str        # "photo" or "video"
    file_base64:  str
    frame_base64: Optional[str] = None  # uncompressed canvas snapshot for video geotag OCR


class AddDeliveryRequest(BaseModel):
    tracking_id:   str
    customer_name: str
    address:       str
    driver_id:     str
    expected_lat:  Optional[float] = None
    expected_lng:  Optional[float] = None
    front_door_w3w: Optional[str] = None
