from __future__ import annotations

import os

import grpc
import pytest

from bookstore_client import BookStoreClient
import bookstore_client.stubs  # noqa: F401  (registers the stubs dir on sys.path)
import bookstore_pb2 as pb2

TARGET = os.environ.get("GRPC_TARGET", "127.0.0.1:50051")


@pytest.fixture(scope="session")
def client() -> BookStoreClient:
    with BookStoreClient(target=TARGET) as c:
        c.wait_until_ready()
        yield c


def test_health_check(client: BookStoreClient) -> None:
    resp = client.health_check()
    assert resp.status == "ok"


def test_list_books_first_page(client: BookStoreClient) -> None:
    # Page size is 2, so page 1 returns the first two of the five seed books.
    resp = client.list_books(page=1)
    assert resp.total == 5
    assert [b.title for b in resp.items] == ["The Great Gatsby", "Sapiens"]
    assert [b.id for b in resp.items] == [1, 2]


def test_list_books_by_genre(client: BookStoreClient) -> None:
    fiction = client.list_books(genre=pb2.FICTION)
    assert fiction.total == 2
    assert [b.title for b in fiction.items] == ["The Great Gatsby", "1984"]


def test_list_books_empty_page(client: BookStoreClient) -> None:
    # A page beyond the last returns no items but the true filtered total.
    resp = client.list_books(genre=pb2.POETRY, page=2)
    assert resp.total == 1
    assert list(resp.items) == []


def test_create_get_and_delete_book(client: BookStoreClient) -> None:
    # The seed store has 5 books, so a new id is 6.
    created = client.create_book(
        title="The Left Hand of Darkness",
        genre=pb2.SCI_FI,
        author="Ursula K. Le Guin",
    )
    assert created.id == 6
    assert created.title == "The Left Hand of Darkness"
    assert created.genre == pb2.SCI_FI
    assert created.author == "Ursula K. Le Guin"

    fetched = client.get_book(created.id)
    assert fetched == created

    deleted = client.delete_book(created.id)
    assert deleted.deleted is True

    # The store is back to its original 5 books.
    after = client.list_books(page=1)
    assert after.total == 5


def test_get_missing_book_is_not_found(client: BookStoreClient) -> None:
    with pytest.raises(grpc.RpcError) as excinfo:
        client.get_book(9999)
    assert excinfo.value.code() == grpc.StatusCode.NOT_FOUND


def test_delete_missing_book_is_not_found(client: BookStoreClient) -> None:
    with pytest.raises(grpc.RpcError) as excinfo:
        client.delete_book(9999)
    assert excinfo.value.code() == grpc.StatusCode.NOT_FOUND
