local logo = {}

local white = image("../../assets/images/Logo_White.png")
local black = image("../../assets/images/Logo_Black.png")

white:resize({ width = 200 })
black:resize({ width = 200 })

function logo.render(output, args)
	local logo = rectangle({
		x = args.x - black.width,
		y = args.y - black.height,
		size = black.size,
	})

	if output:dominant_in(logo):to_oklch().l > 0.5 then
		output:blend(black, { at = logo, color_space = "srgb" })
	else
		output:blend(white, { at = logo, color_space = "srgb" })
	end
end

return logo
