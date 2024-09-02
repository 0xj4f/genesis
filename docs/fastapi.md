# FASTAPI TIPS AND GUIDELINES

## ASYNC I/O TIPS

Understanding the nature of CPU-bound and blocking operations is essential when deciding whether to use async development. Async is excellent for I/O-bound operations where tasks spend a lot of time waiting (e.g., for network or disk I/O). However, it doesn't necessarily provide benefits for CPU-bound operations, which require intensive computation. In some cases, using async for CPU-bound tasks can even degrade performance.

Here’s a list of common CPU-bound and blocking operations that are best handled synchronously or through parallel processing (e.g., using multiprocessing or separate threads):

### 1. **Complex Mathematical Computations**
   - Examples: Large-scale matrix multiplications, numerical simulations, statistical analyses, cryptographic operations.
   - Reason: These tasks involve heavy mathematical operations that consume significant CPU resources. They block the execution thread, so running them asynchronously doesn't free up the event loop.

### 2. **Data Encryption and Decryption**
   - Examples: AES encryption/decryption, RSA key generation, hashing algorithms (SHA-256, MD5).
   - Reason: Cryptographic operations are computationally expensive and consume CPU cycles. Asynchronous execution won't help in reducing the blocking nature of these tasks.

### 3. **Data Compression and Decompression**
   - Examples: Compressing or decompressing large files using formats like ZIP, GZIP, LZMA.
   - Reason: These operations involve reading and processing large chunks of data at a time, consuming significant CPU resources.

### 4. **File Processing with Heavy Computation**
   - Examples: Parsing and analyzing large XML/JSON files, processing huge CSV datasets.
   - Reason: Reading files can be I/O-bound, but if each line requires significant processing (e.g., data transformation, validation), it can become CPU-bound.

### 5. **Image and Video Processing**
   - Examples: Applying filters, transformations, encoding/decoding, resizing, converting formats.
   - Reason: Operations like these involve manipulating pixels, which require significant CPU resources. Libraries like OpenCV and PIL perform such tasks and are better suited for synchronous or parallel processing.

### 6. **Machine Learning Model Training**
   - Examples: Training models using frameworks like TensorFlow, PyTorch, Scikit-Learn.
   - Reason: Training often involves complex computations across vast datasets, requiring intensive use of CPU/GPU resources. These tasks are inherently blocking and are best suited for parallel or distributed computing.

### 7. **Big Data Processing**
   - Examples: Aggregations, transformations, sorting, and filtering large datasets using tools like Pandas or Apache Spark.
   - Reason: Operations on large datasets require iterating over and computing on each data point, which is CPU-bound.

### 8. **Scientific Simulations**
   - Examples: Simulating physical systems, chemical reactions, climate modeling, Monte Carlo simulations.
   - Reason: These tasks involve solving complex mathematical models and equations, which are computationally intensive.

### 9. **Rendering Graphics**
   - Examples: Generating 3D graphics, video game rendering, animation processing.
   - Reason: Graphics rendering involves complex mathematical computations and manipulation of large amounts of data to display images.

### 10. **Search and Sorting Algorithms on Large Datasets**
   - Examples: Sorting large lists, searching for elements in large arrays or databases.
   - Reason: Advanced algorithms, such as quicksort, mergesort, or even simple sorting on large datasets, require significant CPU resources.

### 11. **Regular Expression Processing**
   - Examples: Parsing text with complex regex patterns, large-scale search-and-replace operations.
   - Reason: While regex operations can be fast, complex patterns or large text sizes make them CPU-bound, especially in cases of catastrophic backtracking.

### 12. **PDF Processing and Generation**
   - Examples: Generating reports, modifying or merging PDF files, extracting text from PDFs.
   - Reason: PDF libraries often require manipulating content byte-by-byte, which can be CPU-bound.

### 13. **Statistical Analysis and Data Mining**
   - Examples: Calculating correlations, regressions, clustering, and classification.
   - Reason: These involve processing large datasets with statistical functions, which can be CPU-intensive.

### General Guidelines

1. **Avoid Using Async for CPU-Bound Tasks**: Since async is primarily beneficial for I/O-bound operations, avoid using async/await for tasks that primarily consume CPU resources. For CPU-bound tasks, consider using Python's `concurrent.futures.ThreadPoolExecutor` or `ProcessPoolExecutor` to offload the work to separate threads or processes.

2. **Use Profiling Tools**: Always profile your application to understand where the bottlenecks are. Tools like cProfile, Py-Spy, or line_profiler can help identify CPU-bound tasks.

3. **Consider Multithreading or Multiprocessing**: For tasks that must run concurrently and are CPU-bound, use multithreading (for tasks that involve I/O) or multiprocessing (for CPU-bound tasks) instead of async. Python's `concurrent.futures` or `multiprocessing` module can be helpful.

4. **Offload to Specialized Hardware**: For tasks like machine learning or cryptographic operations, consider using GPUs or specialized hardware accelerators if available.

By keeping these considerations in mind, you can effectively decide when to use asynchronous programming and when to rely on other forms of concurrency or parallelism for CPU-bound tasks.

## LINKS
- https://github.com/kludex/fastapi-dependency
- https://www.youtube.com/watch?v=nYAMtzAbNN8
- https://github.com/kludex/fastapi-dependency
- https://docs.python.org/3/library/asyncio-dev.html#debug-mode
- https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html
- https://github.com/fastapi/full-stack-fastapi-template