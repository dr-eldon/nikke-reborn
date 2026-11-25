local character = {}
local cache = {}

function character.accent(id, skin)
	local key = { id, skin }

	if cache[key] == nil then
		local frame = stream("nikke-viewer", {
			width = 2048,
			height = 2048,
			color_space = "srgb",
			alpha = "premultiplied",
			args = {
				"--stdout",
				"--skin",
				skin or "-",
				"--time",
				0,
				"--half-body",
				id,
			},
		})()

		local tint = frame
			:vivid_in(rectangle({ size = frame.size }))
			:to_oklch()
			:with_alpha(1.0)

		if tint.c > 0.02 and tint.l > 0.5 then
			tint.c = math.max(tint.c, 0.15)
		end

		cache[key] = tint
	end

	return cache[key]:clone()
end

return character
