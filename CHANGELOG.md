# v0.11.3 - 22/11/2024
- Adding instructions block and refactoring form structure

# v0.11.2 - 22/11/2024
- Opening article in new window and setting DOI url in link

# v0.11.1 - 22/11/2024
- Adding validation for experiment ratings

# v0.11.0 - 14/11/2024
- Increasing max number of recommendations for demo

# v0.10.2 - 14/11/2024
- Fixing template lib version

# v0.10.1 - 14/11/2024
- Installing template lib

# v0.10.0 - 14/11/2024
- Experiment page for collecting user evaluations

# v0.9.0 - 14/11/2024
- Experiment page for collecting user evaluations

# v0.9.0 - 14/11/2024
- Evaluation method for algorithm and recommendation system research

# v0.8.2 - 08/11/2024
- Implementing catch for null qualis

# v0.8.1 - 16/09/2024
- Updating libraries and nltk resources

# v0.8.0 - 16/09/2024
- Implementing retry on DBLP adapter for rate limited responses

# v0.7.1 - 28/02/2024
- Changing conditions for user edition validation in db module

# v0.7.0 - 18/02/2024
- Implementing async structure for transactions
- Increasing DBLP article request number from 5 to 15

# v0.6.2 - 11/02/2024
- Fixing validation method for recommendations

# v0.6.1 - 11/02/2024
- Updating library

# v0.6.0 - 07/02/2024
- Improving performance
- Refactoring sanitizing logic and moving it to publication service

# v0.5.1 - 01/02/2024
- Adding missing NLTK download call

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