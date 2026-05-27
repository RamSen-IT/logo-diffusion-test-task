-- KEYS[1] = client:{id}:balance
-- ARGV[1] = cost
local balance = tonumber(redis.call('GET', KEYS[1]))
if balance == nil then
    return redis.error_reply('CLIENT_NOT_FOUND')
end
if balance < tonumber(ARGV[1]) then
    return redis.error_reply('INSUFFICIENT_CREDITS')
end
return redis.call('DECRBY', KEYS[1], ARGV[1])
