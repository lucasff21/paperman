# v0.5.0 - 26/01/2024
- Improving performance
- Refining recommendation process
- Implementing demo route

# v0.4.4 - 29/12/2023
- Reducing number of results per DBLP query

# v0.4.3 - 29/12/2023
- Changing condition priority on validation method for recommendations

# v0.4.2 - 29/12/2023
- Fixing validation method for recommendations

# v0.4.1 - 28/12/2023
- Validation on first result in best publication match method

# v0.4.0 - 28/12/2023
- Adding validation on venue score retrieval to avoid flow break
- Reduction of processing unused words by checking query subject languages
- Changing cache TTL of venues and auth tokens
- Limiting search results to 20 on DBLP API
- Capping three publications per request
- Implementing verification of recommmendations per user

# v0.3.0 - 15/12/2023
- Implementing New Relic integration

# v0.2.1 - 13/11/2023
- Skipping openapi.json for swagger on auth middleware
- Removing swagger from auth middleware check

# v0.2.0 - 13/11/2023
- Removing work and education affiliations

# v0.1.6 - 13/11/2023
- Adding treatment to avoid adding null data from user summary

# v0.1.5 - 13/11/2023
- Setting default value in pop method if venue cache entry has no id

# v0.1.4 - 13/11/2023
- Saving venues on database and cache to avoid DBLP rate limiting

# v0.1.3 - 08/11/2023
- Additional verification for NTLK downloads

# v0.1.2 - 08/11/2023
- Transfering NTLK download logic to function

# v0.1.1 - 08/11/2023
- Adding verification to download NTLK stopwords if not cached

# v0.1.0 - 08/11/2023
- Initial version