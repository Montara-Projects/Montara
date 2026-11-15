from io import BytesIO
from types import SimpleNamespace

from flask import Flask

from urano.native_owner_web_gateway import stream_song_result


def test_private_song_response_streams_and_closes_worker():
    data = b"x" * (512 * 1024 + 1)
    closed = []
    lengths = []
    stream = BytesIO(data)

    def read(n):
        lengths.append(n)
        return stream.read(n)

    upstream = SimpleNamespace(
        status=200, read=read,
        getheader=lambda name, default: {"Content-Type": "video/mp4", "Content-Length": str(len(data))}.get(name, default),
    )
    connection = SimpleNamespace(
        sock=None, request=lambda *args: None, getresponse=lambda: upstream,
        close=lambda: closed.append(True),
    )
    app = Flask(__name__)
    @app.get("/song")
    def song():
        return stream_song_result(lambda: connection, "/api/v1/wizard/song-result/" + "1"*32 + "?project_id=/mine")

    response = app.test_client().get("/song", buffered=False)
    assert response.status_code == 200
    assert response.content_length == len(data)
    assert b"".join(response.response) == data
    response.close()
    assert closed and lengths and max(lengths) == 256 * 1024
