from __future__ import annotations

import logging
import os

import grpc
import pytest

from bookstore_client import BookStoreClient
import bookstore_client.stubs  # noqa: F401  (registers the stubs dir on sys.path)
import bookstore_pb2 as pb2

TARGET = os.environ.get("GRPC_TARGET", "127.0.0.1:50051")

log = logging.getLogger("bookstore.tests")


# --- small logging helpers so every test prints a readable trace --------------

def _genre_name(genre: int) -> str:
    try:
        return pb2.Genre.Name(genre)
    except ValueError:
        return repr(genre)


def _all_books(client: BookStoreClient) -> list[pb2.Book]:
    # Page through the whole store (page size is 2) and return every book in id order.
    books: list[pb2.Book] = []
    page = 1
    while True:
        resp = client.list_books(page=page)
        if not resp.items:
            break
        books.extend(resp.items)
        if len(resp.items) < 2:
            break
        page += 1
    return books


def log_state(client: BookStoreClient, tag: str) -> None:
    books = _all_books(client)
    listing = ", ".join(
        f"#{b.id} {b.title!r} [{_genre_name(b.genre)}]" for b in books
    ) or "(empty)"
    log.info("[%s] initial state: %d book(s) -> %s", tag, len(books), listing)


def log_call(label: str, **fields: object) -> None:
    rendered = " ".join(f"{k}={v!r}" for k, v in fields.items())
    log.info("  %s %s", label, rendered)


def log_expect(label: str, expected: object, actual: object) -> bool:
    matched = expected == actual
    log.info(
        "  expect %-22s got %-30s expected %-30s -> %s",
        label,
        actual,
        expected,
        "MATCH" if matched else "MISMATCH",
    )
    return matched


@pytest.fixture(scope="session")
def client() -> BookStoreClient:
    with BookStoreClient(target=TARGET) as c:
        c.wait_until_ready()
        log.info("Connected to gRPC target %s", TARGET)
        yield c


# --- health ------------------------------------------------------------------

def test_health_check(client: BookStoreClient) -> None:
    log.info("--- test_health_check ---")
    log_call("HealthCheck", request="HealthRequest()")
    resp = client.health_check()
    log_expect("status", "ok", resp.status)
    assert log_expect("status", "ok", resp.status)


# --- list: pagination --------------------------------------------------------

def test_list_first_page(client: BookStoreClient) -> None:
    log.info("--- test_list_first_page ---")
    log_state(client, "list_first_page")
    log_call("ListBooks", genre=pb2.GENRE_UNSPECIFIED, page=1)
    resp = client.list_books(page=1)
    log_expect("total", 5, resp.total)
    log_expect("titles", ["The Great Gatsby", "Sapiens"], [b.title for b in resp.items])
    log_expect("ids", [1, 2], [b.id for b in resp.items])
    assert log_expect("total", 5, resp.total)
    assert [b.title for b in resp.items] == ["The Great Gatsby", "Sapiens"]
    assert [b.id for b in resp.items] == [1, 2]


def test_list_second_page(client: BookStoreClient) -> None:
    log.info("--- test_list_second_page ---")
    log_call("ListBooks", genre=pb2.GENRE_UNSPECIFIED, page=2)
    resp = client.list_books(page=2)
    log_expect("titles", ["Dune", "Leaves of Grass"], [b.title for b in resp.items])
    log_expect("ids", [3, 4], [b.id for b in resp.items])
    assert [b.title for b in resp.items] == ["Dune", "Leaves of Grass"]
    assert [b.id for b in resp.items] == [3, 4]


def test_list_last_partial_page(client: BookStoreClient) -> None:
    log.info("--- test_list_last_partial_page ---")
    log_call("ListBooks", genre=pb2.GENRE_UNSPECIFIED, page=3)
    resp = client.list_books(page=3)
    log_expect("total", 5, resp.total)
    log_expect("titles", ["1984"], [b.title for b in resp.items])
    assert resp.total == 5
    assert [b.title for b in resp.items] == ["1984"]


@pytest.mark.parametrize("page", [4, 10, 1000])
def test_list_beyond_last_page(client: BookStoreClient, page: int) -> None:
    log.info("--- test_list_beyond_last_page (page=%d) ---", page)
    log_call("ListBooks", genre=pb2.GENRE_UNSPECIFIED, page=page)
    resp = client.list_books(page=page)
    log_expect("items", [], list(resp.items))
    log_expect("total", 5, resp.total)
    assert list(resp.items) == []
    assert resp.total == 5


# --- list: non-positive page coercion ----------------------------------------

@pytest.mark.parametrize("page", [0, -1, -5])
def test_nonpositive_page_coerced_to_one(client: BookStoreClient, page: int) -> None:
    log.info("--- test_nonpositive_page_coerced_to_one (page=%d) ---", page)
    log_call("ListBooks", genre=pb2.GENRE_UNSPECIFIED, page=page)
    resp = client.list_books(page=page)
    log_expect("titles (== page 1)", ["The Great Gatsby", "Sapiens"], [b.title for b in resp.items])
    log_expect("total", 5, resp.total)
    assert [b.title for b in resp.items] == ["The Great Gatsby", "Sapiens"]
    assert resp.total == 5


# --- list: filtering ---------------------------------------------------------

@pytest.mark.parametrize(
    "genre, titles, total",
    [
        (pb2.FICTION, ["The Great Gatsby", "1984"], 2),
        (pb2.NONFICTION, ["Sapiens"], 1),
        (pb2.SCI_FI, ["Dune"], 1),
        (pb2.POETRY, ["Leaves of Grass"], 1),
    ],
)
def test_list_by_genre(client: BookStoreClient, genre: int, titles: list[str], total: int) -> None:
    log.info("--- test_list_by_genre (%s) ---", _genre_name(genre))
    log_call("ListBooks", genre=_genre_name(genre), page=1)
    resp = client.list_books(genre=genre)
    log_expect("total", total, resp.total)
    log_expect("titles", titles, [b.title for b in resp.items])
    assert resp.total == total
    assert [b.title for b in resp.items] == titles


def test_unspecified_genre_means_no_filter(client: BookStoreClient) -> None:
    log.info("--- test_unspecified_genre_means_no_filter ---")
    log_call("ListBooks", genre=pb2.GENRE_UNSPECIFIED, page=1)
    filtered = client.list_books(genre=pb2.GENRE_UNSPECIFIED)
    unfiltered = client.list_books()
    log_expect("total (filtered vs default)", unfiltered.total, filtered.total)
    assert filtered.total == unfiltered.total == 5


# --- get ---------------------------------------------------------------------

def test_get_existing_book(client: BookStoreClient) -> None:
    log.info("--- test_get_existing_book ---")
    log_call("GetBook", id=3)
    book = client.get_book(3)
    log_expect("title", "Dune", book.title)
    log_expect("genre", pb2.SCI_FI, book.genre)
    log_expect("author", "Frank Herbert", book.author)
    assert book.title == "Dune"
    assert book.genre == pb2.SCI_FI
    assert book.author == "Frank Herbert"


def test_get_missing_book_is_not_found(client: BookStoreClient) -> None:
    log.info("--- test_get_missing_book_is_not_found ---")
    log_call("GetBook", id=9999)
    with pytest.raises(grpc.RpcError) as excinfo:
        client.get_book(9999)
    code = excinfo.value.code()
    log_expect("status code", grpc.StatusCode.NOT_FOUND, code)
    assert code == grpc.StatusCode.NOT_FOUND


# --- create ------------------------------------------------------------------

def test_create_book_full_roundtrip(client: BookStoreClient) -> None:
    log.info("--- test_create_book_full_roundtrip ---")
    log_state(client, "create_full")
    log_call("CreateBook", title="The Left Hand of Darkness", genre=pb2.SCI_FI,
             author="Ursula K. Le Guin")
    created = client.create_book(
        title="The Left Hand of Darkness",
        genre=pb2.SCI_FI,
        author="Ursula K. Le Guin",
    )
    log_expect("assigned id", 6, created.id)
    log_expect("title", "The Left Hand of Darkness", created.title)
    log_expect("genre", pb2.SCI_FI, created.genre)
    log_expect("author", "Ursula K. Le Guin", created.author)
    assert created.id == 6
    assert created.title == "The Left Hand of Darkness"
    assert created.genre == pb2.SCI_FI
    assert created.author == "Ursula K. Le Guin"

    # It is immediately visible and equal on fetch.
    fetched = client.get_book(created.id)
    log_expect("fetched == created", True, fetched == created)
    assert fetched == created

    # Self-clean: the store returns to its original five books.
    deleted = client.delete_book(created.id)
    log_expect("deleted", True, deleted.deleted)
    assert deleted.deleted is True
    assert client.list_books(page=1).total == 5


def test_create_book_omits_optional_fields(client: BookStoreClient) -> None:
    log.info("--- test_create_book_omits_optional_fields ---")
    log_call("CreateBook", title="A Minimal Book", author="(omitted)", genre="(omitted)")
    created = client.create_book(title="A Minimal Book")
    log_expect("assigned id", 6, created.id)
    log_expect("genre (unspecified)", pb2.GENRE_UNSPECIFIED, created.genre)
    log_expect("author (empty)", "", created.author)
    # An unspecified genre means it is not found under a genre filter.
    fiction = client.list_books(genre=pb2.FICTION)
    log_expect("not under FICTION", True, created.title not in [b.title for b in fiction.items])
    assert created.genre == pb2.GENRE_UNSPECIFIED
    assert created.author == ""
    assert created.title not in [b.title for b in fiction.items]
    client.delete_book(created.id)


@pytest.mark.parametrize("title", ["", "   ", " \t\n "])
def test_create_book_rejects_empty_title(client: BookStoreClient, title: str) -> None:
    log.info("--- test_create_book_rejects_empty_title (title=%r) ---", title)
    log_call("CreateBook", title=title, genre=pb2.FICTION)
    with pytest.raises(grpc.RpcError) as excinfo:
        client.create_book(title=title, genre=pb2.FICTION)
    code = excinfo.value.code()
    log_expect("status code", grpc.StatusCode.INVALID_ARGUMENT, code)
    assert code == grpc.StatusCode.INVALID_ARGUMENT
    # Nothing was created: the store is unchanged.
    assert client.list_books(page=1).total == 5


# --- delete ------------------------------------------------------------------

def test_delete_existing_book_then_gone(client: BookStoreClient) -> None:
    log.info("--- test_delete_existing_book_then_gone ---")
    log_state(client, "delete_existing")
    log_call("CreateBook", title="To Be Deleted", genre=pb2.POETRY)
    created = client.create_book(title="To Be Deleted", genre=pb2.POETRY)
    log_expect("total after create", 6, client.list_books(page=1).total)
    assert client.list_books(page=1).total == 6

    log_call("DeleteBook", id=created.id)
    resp = client.delete_book(created.id)
    log_expect("deleted", True, resp.deleted)
    assert resp.deleted is True

    # The book is gone: get now reports NOT_FOUND and the total is back to 5.
    with pytest.raises(grpc.RpcError) as excinfo:
        client.get_book(created.id)
    log_expect("get after delete", grpc.StatusCode.NOT_FOUND, excinfo.value.code())
    assert excinfo.value.code() == grpc.StatusCode.NOT_FOUND
    assert client.list_books(page=1).total == 5


def test_delete_missing_book_is_not_found(client: BookStoreClient) -> None:
    log.info("--- test_delete_missing_book_is_not_found ---")
    log_call("DeleteBook", id=9999)
    with pytest.raises(grpc.RpcError) as excinfo:
        client.delete_book(9999)
    code = excinfo.value.code()
    log_expect("status code", grpc.StatusCode.NOT_FOUND, code)
    assert code == grpc.StatusCode.NOT_FOUND
