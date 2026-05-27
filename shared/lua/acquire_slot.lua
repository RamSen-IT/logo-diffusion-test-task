-- KEYS[1] = rate:{client_id}:active
-- ARGV[1] = max_concurrent
local current = tonumber(redis.call('GET', KEYS[1])) or 0
if current >= tonumber(ARGV[1]) then
    return redis.error_reply('RATE_LIMIT_EXCEEDED')
end
redis.call('INCR', KEYS[1])
redis.call('EXPIRE', KEYS[1], 300)
return current + 1
