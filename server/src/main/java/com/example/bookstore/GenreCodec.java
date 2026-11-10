package com.example.bookstore;

import java.util.Locale;

// Translates between the proto Genre enum and the string used in the JSON data
// file. The proto's GENRE_UNSPECIFIED maps to an empty string, which is also how
// "no genre" is represented when listing (no filter) or when a create request omits
// the field.
final class GenreCodec {

    private GenreCodec() {}

    static Genre fromJson(String json) {
        if (json == null || json.isBlank()) {
            return Genre.GENRE_UNSPECIFIED;
        }
        return switch (json.toLowerCase(Locale.ROOT)) {
            case "fiction" -> Genre.FICTION;
            case "nonfiction" -> Genre.NONFICTION;
            case "sci-fi" -> Genre.SCI_FI;
            case "poetry" -> Genre.POETRY;
            default -> Genre.GENRE_UNSPECIFIED;
        };
    }

    static String toJson(Genre genre) {
        return switch (genre) {
            case FICTION -> "fiction";
            case NONFICTION -> "nonfiction";
            case SCI_FI -> "sci-fi";
            case POETRY -> "poetry";
            default -> "";
        };
    }
}
