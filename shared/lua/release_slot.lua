-- KEYS[1] = rate:{client_id}:active
local current = tonumber(redis.call('GET', KEYS[1])) or 0
if current > 0 then
    redis.call('DECR', KEYS[1])
end
return redis.status_reply('OK')
