local manufacturer = {}

local map = {
	elysion = image("../../assets/images/logos/ELYSION.png"),
	tetra = image("../../assets/images/logos/TETRA.png"),
	missilis = image("../../assets/images/logos/MISSILIS.png"),
	pilgrim = image("../../assets/images/logos/PILGRIM.png"),
	abnormal = image("../../assets/images/logos/ABNORMAL.png"),
}

for key, manufacturer in pairs(map) do
	if manufacturer.width > manufacturer.height then
		manufacturer:resize({ width = 220 })
	else
		manufacturer:resize({ height = 180 })
	end

	local inverted = manufacturer:clone()
	inverted:invert()
	inverted:recolor("#222222")

	map[key] = { manufacturer, inverted }
end

function manufacturer.render(output, name, inset)
	local white, black = table.unpack(map[name])

	if inset.x < 0 then
		inset.x = inset.x + output.width - white.width
	end

	if inset.y < 0 then
		inset.y = inset.y + output.height - white.height
	end

	local region = rectangle({ x = inset.x, y = inset.y, size = white.size })

	if output:luma_in(region) < 128 then
		output:blend(white, {
			at = region,
			color_space = "srgb",
		})
	else
		output:blend(black, {
			at = region,
			color_space = "srgb",
		})
	end
end

return manufacturer
