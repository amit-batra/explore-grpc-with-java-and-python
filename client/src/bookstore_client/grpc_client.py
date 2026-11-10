from __future__ import annotations

import grpc

import bookstore_client.stubs  # noqa: F401  (registers the stubs dir on sys.path)
import bookstore_pb2 as pb2
import bookstore_pb2_grpc as pb2_grpc


# A thin wrapper over the generated gRPC stub. Each method maps one RPC; the
# wrapper exists so the demo and the tests never touch the generated stub
# directly and so the target address is configurable.
class BookStoreClient:
    def __init__(self, target: str = "127.0.0.1:50051", timeout: float = 10.0) -> None:
        self._channel = grpc.insecure_channel(target)
        self._stub = pb2_grpc.BookServiceStub(self._channel)
        self._timeout = timeout

    def __enter__(self) -> "BookStoreClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._channel.close()

    # Wait until the channel is ready (server reachable) or raise on timeout.
    def wait_until_ready(self, timeout: float | None = None) -> None:
        grpc.channel_ready_future(self._channel).result(timeout or self._timeout)

    def health_check(self) -> pb2.HealthResponse:
        return self._stub.HealthCheck(pb2.HealthRequest(), timeout=self._timeout)

    def list_books(
        self,
        genre: int = pb2.GENRE_UNSPECIFIED,
        page: int = 1,
    ) -> pb2.ListBooksResponse:
        return self._stub.ListBooks(
            pb2.ListBooksRequest(genre=genre, page=page), timeout=self._timeout
        )

    def create_book(
        self,
        title: str,
        genre: int = pb2.GENRE_UNSPECIFIED,
        author: str = "",
    ) -> pb2.Book:
        return self._stub.CreateBook(
            pb2.CreateBookRequest(title=title, genre=genre, author=author),
            timeout=self._timeout,
        )

    def get_book(self, book_id: int) -> pb2.Book:
        return self._stub.GetBook(pb2.GetBookRequest(id=book_id), timeout=self._timeout)

    def delete_book(self, book_id: int) -> pb2.DeleteBookResponse:
        return self._stub.DeleteBook(
            pb2.DeleteBookRequest(id=book_id), timeout=self._timeout
        )
