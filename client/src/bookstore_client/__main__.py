from __future__ import annotations

import os
import sys

import grpc

from bookstore_client import BookStoreClient
import bookstore_client.stubs  # noqa: F401  (registers the stubs dir on sys.path)
import bookstore_pb2 as pb2


# Genre enum values mirror proto/bookstore.proto.
SCI_FI = pb2.SCI_FI  # == 3

TARGET = os.environ.get("GRPC_TARGET", "127.0.0.1:50051")


def main() -> int:
    print(f"Connecting to {TARGET}\n")
    with BookStoreClient(target=TARGET) as client:
        client.wait_until_ready()

        # --- HealthCheck -----------------------------------------------------
        health = client.health_check()
        print(f"HealthCheck -> status={health.status!r}")
        assert health.status == "ok"

        # --- ListBooks (page 1 of all genres) --------------------------------
        page1 = client.list_books(page=1)
        titles = [b.title for b in page1.items]
        print(f"ListBooks(page=1) -> total={page1.total}, items={titles}")
        assert page1.total == 5, f"expected 5 books, got {page1.total}"
        assert titles == ["The Great Gatsby", "Sapiens"], titles

        # --- ListBooks filtered by genre -------------------------------------
        fiction = client.list_books(genre=pb2.FICTION)
        f_titles = [b.title for b in fiction.items]
        print(f"ListBooks(genre=fiction) -> total={fiction.total}, items={f_titles}")
        assert fiction.total == 2, f"expected 2 fiction books, got {fiction.total}"
        assert f_titles == ["The Great Gatsby", "1984"], f_titles

        # --- CreateBook ------------------------------------------------------
        created = client.create_book(
            title="The Left Hand of Darkness",
            genre=SCI_FI,
            author="Ursula K. Le Guin",
        )
        print(f"CreateBook -> id={created.id}, title={created.title!r}, "
              f"genre={created.genre}, author={created.author!r}")
        assert created.id == 6, f"expected new id 6, got {created.id}"
        assert created.title == "The Left Hand of Darkness"
        assert created.genre == SCI_FI
        assert created.author == "Ursula K. Le Guin"

        # --- GetBook ---------------------------------------------------------
        fetched = client.get_book(created.id)
        print(f"GetBook({created.id}) -> id={fetched.id}, title={fetched.title!r}")
        assert fetched == created, "fetched book should equal the created book"

        # --- GetBook of a missing id -> NOT_FOUND ----------------------------
        try:
            client.get_book(9999)
            raise AssertionError("expected NotFound for missing book")
        except grpc.RpcError as exc:
            print(f"GetBook(9999) -> {exc.code().name} (as expected)")
            assert exc.code() == grpc.StatusCode.NOT_FOUND

        # --- DeleteBook ------------------------------------------------------
        deleted = client.delete_book(created.id)
        print(f"DeleteBook({created.id}) -> deleted={deleted.deleted}")
        assert deleted.deleted is True

        # --- DeleteBook of a missing id -> NOT_FOUND -------------------------
        try:
            client.delete_book(9999)
            raise AssertionError("expected NotFound for missing book")
        except grpc.RpcError as exc:
            print(f"DeleteBook(9999) -> {exc.code().name} (as expected)")
            assert exc.code() == grpc.StatusCode.NOT_FOUND

        # --- ListBooks after create+delete leaves the store unchanged --------
        after = client.list_books(page=1)
        print(f"ListBooks(after) -> total={after.total}")
        assert after.total == 5, "store should be back to 5 books"

        print("\nAll assertions passed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
