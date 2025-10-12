curl -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DAILY_API_KEY" \
  -XDELETE \
  https://api.daily.co/v1/release-phone-number/$1
        