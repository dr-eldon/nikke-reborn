local logo = {}

local white = image("../../assets/images/Logo_White.png")
local black = image("../../assets/images/Logo_Black.png")

white:resize({ width = 200 })
black:resize({ width = 200 })

function logo.render(output, inset)
	if inset.x < 0 then
		inset.x = inset.x + output.width - black.width
	end

	if inset.y < 0 then
		inset.y = inset.y + output.height - black.height
	end

	local logo = rectangle({
		x = inset.x,
		y = inset.y,
		size = black.size,
	})

	if output:dominant_in(logo):to_oklch().l > 0.5 then
		output:blend(black, { at = logo, color_space = "srgb" })
	else
		output:blend(white, { at = logo, color_space = "srgb" })
	end
end

return logo
