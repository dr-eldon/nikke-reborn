local manufacturer = {}

local map = {
	elysion = image("../../assets/images/logos/ELYSION.png"),
	tetra = image("../../assets/images/logos/TETRA.png"),
	missilis = image("../../assets/images/logos/MISSILIS.png"),
	pilgrim = image("../../assets/images/logos/PILGRIM.png"),
	abnormal = image("../../assets/images/logos/ABNORMAL.png"),
}

for _, manufacturer in pairs(map) do
	manufacturer:resize({ width = 170 })
	manufacturer:invert()
end

function manufacturer.render(output, name, inset)
	local manufacturer = map[name]

	if inset.x < 0 then
		inset.x = inset.x + output.width - manufacturer.width
	end

	if inset.y < 0 then
		inset.y = inset.y + output.height - manufacturer.height
	end

	output:blend(manufacturer, {
		at = rectangle({ x = inset.x, y = inset.y, size = manufacturer.size }),
		color_space = "srgb",
	})
end

return manufacturer
