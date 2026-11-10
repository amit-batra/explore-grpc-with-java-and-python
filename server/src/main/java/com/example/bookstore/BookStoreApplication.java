package com.example.bookstore;

import io.grpc.Server;
import io.grpc.ServerBuilder;

import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.TimeUnit;

// Starts the gRPC server and blocks until the process is interrupted.
public final class BookStoreApplication {

    private BookStoreApplication() {}

    public static void main(String[] args) throws IOException, InterruptedException {
        int port = Integer.parseInt(System.getProperty("port", System.getenv().getOrDefault("BOOKSTORE_PORT", "50051")));

        Path dataFile = resolveDataFile();
        BookStoreRepository store = new BookStoreRepository(dataFile);

        Server server = ServerBuilder.forPort(port)
                .addService(new BookServiceImpl(store))
                .build()
                .start();

        System.out.println("Book gRPC server listening on port " + port);
        System.out.println("Backing data file: " + dataFile.toAbsolutePath());
        Runtime.getRuntime().addShutdownHook(new Thread(server::shutdown));

        server.awaitTermination();
    }

    private static Path resolveDataFile() {
        String override = System.getProperty("dataFile", System.getenv().get("BOOKS_DATA_FILE"));
        if (override != null && !override.isBlank()) {
            return Paths.get(override);
        }
        return Paths.get("data", "books.json");
    }
}
