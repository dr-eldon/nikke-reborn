local logo = {}

local white = image("../../assets/images/Logo_White.png")
local black = image("../../assets/images/Logo_Black.png")
local invert = nil

local white_small = white:clone()
white_small:resize({ width = 200 })

local black_small = black:clone()
black_small:resize({ width = 200 })

function logo.render(output, inset)
	if inset.x < 0 then
		inset.x = inset.x + output.width - black_small.width
	end

	if inset.y < 0 then
		inset.y = inset.y + output.height - black_small.height
	end

	local logo = rectangle({
		x = inset.x,
		y = inset.y,
		size = black_small.size,
	})

	if invert == nil then
		invert = output:dominant_in(logo):to_oklch().l > 0.5
	end

	if invert then
		output:blend(black_small, { at = logo, color_space = "srgb" })
	else
		output:blend(white_small, { at = logo, color_space = "srgb" })
	end
end

function logo.glowing(output, args)
	local logo = white:clone()
	logo:resize({ width = args.width, height = args.height })

	local x, y = table.unpack(args.position(logo.width, logo.height))

	local bounds = rectangle({
		x = x,
		y = y,
		size = logo.size,
	})

	local radius = math.floor(logo.width / 20)
	local tint = output:dominant_in(bounds):to_oklch()

	if tint.l > 0.7 then
		logo = black:clone()
		logo:resize({ width = args.width, height = args.height })
		radius = radius / 3
		tint.c = 0.3
		tint.l = 0.8
		tint.a = 0.4
	elseif tint.l > 0.5 then
		tint.c = 0.3
		tint.l = 0.2
		tint.a = 0.5
	else
		tint.c = 0.2
		tint.l = 0.65
		tint.a = 0.4
	end

	bounds = bounds:padded(radius)

	local glowing = blank({
		width = bounds.width,
		height = bounds.height,
	})
	glowing:blend(logo, {
		at = rectangle({ x = radius, y = radius, size = logo.size }),
	})

	glowing:recolor(tint)
	glowing:blur(radius)
	output:blend(glowing, { at = bounds })

	output:blend(logo, {
		at = rectangle({
			x = bounds.x + radius,
			y = bounds.y + radius,
			size = logo.size,
		}),
		color_space = "srgb",
	})
end

function logo.reset()
	invert = nil
end

return logo
