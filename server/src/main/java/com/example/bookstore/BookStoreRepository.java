package com.example.bookstore;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.locks.ReentrantLock;

// A tiny file-backed store. State is persisted in a JSON array of book objects
// (e.g. data/books.json). A ReentrantLock guards each read-modify-write so that
// concurrent requests cannot overwrite one another.
public class BookStoreRepository {

    private static final int PAGE_SIZE = 2;

    private final Path dataFile;
    private final ObjectMapper mapper = new ObjectMapper()
            .enable(SerializationFeature.INDENT_OUTPUT);
    private final ReentrantLock lock = new ReentrantLock();

    public BookStoreRepository(Path dataFile) {
        this.dataFile = dataFile;
    }

    public boolean isHealthy() {
        return true;
    }

    // Total number of books matching the filter, ignoring pagination.
    public int count(Genre genreFilter) {
        lock.lock();
        try {
            List<Book> books = load();
            if (genreFilter == Genre.GENRE_UNSPECIFIED) {
                return books.size();
            }
            return (int) books.stream().filter(b -> b.genre == genreFilter).count();
        } finally {
            lock.unlock();
        }
    }

    public List<Book> list(Genre genreFilter, int page) {
        lock.lock();
        try {
            List<Book> books = load();
            if (genreFilter != Genre.GENRE_UNSPECIFIED) {
                books = books.stream()
                        .filter(b -> b.genre == genreFilter)
                        .toList();
            }
            int start = Math.max(0, (page - 1) * PAGE_SIZE);
            if (start >= books.size()) {
                return new ArrayList<>();
            }
            int end = Math.min(books.size(), start + PAGE_SIZE);
            List<Book> items = new ArrayList<>(books.subList(start, end));
            return items;
        } finally {
            lock.unlock();
        }
    }

    // Returns the created book. The id is server-assigned as max(existing)+1.
    public Book create(String title, Genre genre, String author) {
        lock.lock();
        try {
            List<Book> books = load();
            int nextId = books.stream()
                    .mapToInt(b -> b.id)
                    .max()
                    .orElse(0)
                    + 1;
            Book created = new Book(nextId, title, genre, author == null ? "" : author);
            books.add(created);
            save(books);
            return created;
        } finally {
            lock.unlock();
        }
    }

    // Returns the book or null if no book has the given id.
    public Book get(int id) {
        lock.lock();
        try {
            for (Book book : load()) {
                if (book.id == id) {
                    return book;
                }
            }
            return null;
        } finally {
            lock.unlock();
        }
    }

    // Returns true if a book was removed, false if the id did not exist.
    public boolean delete(int id) {
        lock.lock();
        try {
            List<Book> books = load();
            boolean removed = books.removeIf(b -> b.id == id);
            if (removed) {
                save(books);
            }
            return removed;
        } finally {
            lock.unlock();
        }
    }

    private List<Book> load() {
        if (!Files.exists(dataFile)) {
            return new ArrayList<>();
        }
        try {
            List<Map<String, Object>> rows = mapper.readValue(
                    dataFile.toFile(),
                    new TypeReference<List<Map<String, Object>>>() {});
            List<Book> books = new ArrayList<>(rows.size());
            for (Map<String, Object> row : rows) {
                int id = ((Number) row.get("id")).intValue();
                String title = String.valueOf(row.getOrDefault("title", ""));
                Genre genre = GenreCodec.fromJson(String.valueOf(row.getOrDefault("genre", "")));
                String author = String.valueOf(row.getOrDefault("author", ""));
                books.add(new Book(id, title, genre, author));
            }
            return books;
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to read " + dataFile, e);
        }
    }

    private void save(List<Book> books) {
        try {
            Files.createDirectories(dataFile.getParent());
            List<Map<String, Object>> rows = new ArrayList<>(books.size());
            for (Book book : books) {
                Map<String, Object> row = new java.util.LinkedHashMap<>();
                row.put("id", book.id);
                row.put("title", book.title);
                row.put("genre", GenreCodec.toJson(book.genre));
                row.put("author", book.author);
                rows.add(row);
            }
            mapper.writeValue(dataFile.toFile(), rows);
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to write " + dataFile, e);
        }
    }

    // A plain book record. The fields are kept public to avoid boilerplate
    // accessors in this small demo.
    record Book(int id, String title, Genre genre, String author) {}
}
