curl --location --request POST 'https://api.daily.co/v1/domain-dialin-config' \
    --header "Authorization: Bearer $DAILY_API_KEY" \
    --header 'Content-Type: application/json' \
    --data-raw '{
        "type": "pinless_dialin",
        "phone_number": "+12096553791",
        "room_creation_api": "https://nonhierarchic-husklike-irmgard.ngrok-free.dev/start",
        "name_prefix": "my-pinless-phone",
        "timeout_config": {
            "message": "agent not available. Please call later"
        }
    }'
