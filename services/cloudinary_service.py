import uuid as uuid_pkg

import cloudinary
import cloudinary.uploader

from config import load_settings

settings = load_settings()

if settings.cloudinary_configured:
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


def upload_chat_image(file_bytes: bytes) -> str:
    if not settings.cloudinary_configured:
        raise ValueError("Cloudinary no configurado")

    public_id = f"chat/{uuid_pkg.uuid4()}"
    result = cloudinary.uploader.upload(
        file_bytes,
        public_id=public_id,
        resource_type="image",
    )
    return result["secure_url"]
