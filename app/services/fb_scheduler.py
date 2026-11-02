"""
Schedules a photo post on a Facebook Page (native scheduling: 10 minutes to 30 days ahead).
Login/OAuth stays in your existing /facebook router.
Optional env: FACEBOOK_GRAPH_VERSION (default matches your router: v19.0)
"""
import json
import os

import requests


def _graph() -> str:
    return f"https://graph.facebook.com/{os.getenv('FACEBOOK_GRAPH_VERSION', 'v19.0')}"


def _check(r: requests.Response) -> dict:
    data = r.json()
    if not r.ok:
        err = data.get("error", {})
        raise RuntimeError(f"Facebook: {err.get('message', r.text[:200])} (code {err.get('code')})")
    return data


def schedule_photo_post(page_id: str, page_token: str, image_bytes: bytes,
                        caption: str, unix_time: int) -> str:
    """Uploads the image as a temporary photo, then creates a scheduled post. Returns the post id."""
    photo = _check(requests.post(
        f"{_graph()}/{page_id}/photos",
        data={"published": "false", "temporary": "true", "access_token": page_token},
        files={"source": ("ad.png", image_bytes, "image/png")},
        timeout=120,
    ))
    post = _check(requests.post(
        f"{_graph()}/{page_id}/feed",
        data={
            "message": caption,
            "attached_media[0]": json.dumps({"media_fbid": photo["id"]}),
            "published": "false",
            "unpublished_content_type": "SCHEDULED",
            "scheduled_publish_time": str(unix_time),
            "access_token": page_token,
        },
        timeout=60,
    ))
    return post["id"]


def delete_post(post_id: str, page_token: str) -> None:
    _check(requests.delete(f"{_graph()}/{post_id}", params={"access_token": page_token}, timeout=30))