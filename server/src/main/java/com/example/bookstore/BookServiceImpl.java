package com.example.bookstore;

import io.grpc.Status;
import io.grpc.stub.StreamObserver;

import java.util.List;

// Implements the BookService RPCs, delegating to a JSON-backed repository.
//
// Note: the proto generates a message class named `Book` in this very package, so
// the repository's `BookStoreRepository.Book` record must be referenced by its
// fully-qualified name here; the unqualified `Book` is the proto message.
//
// Validation failures surface as gRPC status codes:
//   INVALID_ARGUMENT -> bad page number or empty title
//   NOT_FOUND        -> get/delete of a missing book
public class BookServiceImpl extends BookServiceGrpc.BookServiceImplBase {

    private final BookStoreRepository store;

    public BookServiceImpl(BookStoreRepository store) {
        this.store = store;
    }

    @Override
    public void healthCheck(HealthRequest request, StreamObserver<HealthResponse> responseObserver) {
        responseObserver.onNext(HealthResponse.newBuilder().setStatus("ok").build());
        responseObserver.onCompleted();
    }

    @Override
    public void listBooks(ListBooksRequest request, StreamObserver<ListBooksResponse> responseObserver) {
        int page = request.getPage() <= 0 ? 1 : request.getPage();
        if (page < 1) {
            invalidArgument(responseObserver, "page must be >= 1");
            return;
        }
        Genre filter = request.getGenre() == Genre.GENRE_UNSPECIFIED ? Genre.GENRE_UNSPECIFIED : request.getGenre();

        List<BookStoreRepository.Book> items = store.list(filter, page);

        ListBooksResponse.Builder builder = ListBooksResponse.newBuilder().setTotal(store.count(filter));
        for (BookStoreRepository.Book item : items) {
            builder.addItems(toProto(item));
        }
        responseObserver.onNext(builder.build());
        responseObserver.onCompleted();
    }

    @Override
    public void createBook(CreateBookRequest request, StreamObserver<Book> responseObserver) {
        if (request.getTitle().isBlank()) {
            invalidArgument(responseObserver, "title must not be empty");
            return;
        }
        Genre genre = request.getGenre();
        BookStoreRepository.Book created = store.create(request.getTitle(), genre, request.getAuthor());
        responseObserver.onNext(toProto(created));
        responseObserver.onCompleted();
    }

    @Override
    public void getBook(GetBookRequest request, StreamObserver<Book> responseObserver) {
        BookStoreRepository.Book found = store.get(request.getId());
        if (found == null) {
            notFound(responseObserver, request.getId());
            return;
        }
        responseObserver.onNext(toProto(found));
        responseObserver.onCompleted();
    }

    @Override
    public void deleteBook(DeleteBookRequest request, StreamObserver<DeleteBookResponse> responseObserver) {
        boolean removed = store.delete(request.getId());
        if (!removed) {
            notFound(responseObserver, request.getId());
            return;
        }
        responseObserver.onNext(DeleteBookResponse.newBuilder().setDeleted(true).build());
        responseObserver.onCompleted();
    }

    private static Book toProto(BookStoreRepository.Book book) {
        return Book.newBuilder()
                .setId(book.id())
                .setTitle(book.title())
                .setGenre(book.genre())
                .setAuthor(book.author())
                .build();
    }

    private static <T> void invalidArgument(StreamObserver<T> obs, String detail) {
        obs.onError(Status.INVALID_ARGUMENT.withDescription(detail).asRuntimeException());
    }

    private static <T> void notFound(StreamObserver<T> obs, int id) {
        obs.onError(Status.NOT_FOUND.withDescription("Book with id " + id + " does not exist.")
                .asRuntimeException());
    }
}
