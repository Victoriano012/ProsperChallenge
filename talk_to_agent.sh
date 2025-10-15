curl --location --request POST 'https://api.pipecat.daily.co/v1/public/prosperbot/start' \
  --header "Authorization: Bearer $PIPECAT_API_KEY" \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "createDailyRoom": true,
    "body": {"custom": "data"}
  }' | jq -r '"Join the call at \(.dailyRoom)?t=\(.dailyToken)"'
