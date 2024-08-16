#

## DATABASE 

mysql: heavy read
postgre: heavy write
mongoDB: flexibility



## PRODUCTION TO DO
- rate limiting
- csrf


### Optimization improvements

Error Handling & Logging:

Consider improving error handling in database operations by adding more granular logging to capture the nature of exceptions.
Security Enhancements:

Rate Limiting: Implement rate limiting on sensitive endpoints like /token to prevent brute-force attacks.
Stronger Password Policies: Consider enforcing stronger password policies (e.g., minimum length, complexity) during user creation.
