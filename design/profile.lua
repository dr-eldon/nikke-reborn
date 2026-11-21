local copyright = require("nikke.copyright")
local logo = require("nikke.logo")
local manufacturer = require("nikke.manufacturer")
local title = require("nikke.title")

local profile = {}
local width = 1640
local height = 2048
local cache = {}

local mask = image("../assets/images/designs/Card_Mask_Profile.png")
mask:resize({ width = width, height = height })

profile.arguments = {
	"id",
	"background",
	"manufacturer",
	"title",
	"subtitle",
	"reel",
	"skin",
}

function profile.render(args)
	args.reel = args.reel or ""

	if cache[args.background] == nil then
		local base =
			image("../assets/images/backgrounds/" .. args.background .. ".png")

		base:autocontrast()
		base:resize({ width = width, height = height, mode = "cover" })
		base:convert("srgb")

		cache[args.background] = base
	end

	local base = cache[args.background]

	local reel = {}

	for expression in string.gmatch(args.reel, "([^,]+)") do
		local size = math.floor(base.width / 7)

		local render = stream("nikke-viewer", {
			width = size,
			height = size,
			color_space = "srgb",
			alpha = "premultiplied",
			args = {
				args.id,
				"--stdout",
				"--portrait",
				"--skin",
				args.skin or "-",
				"--animation",
				expression,
				"--time",
				0,
			},
		})

		local face = blank({ width = size, height = size, color = "#FFFFFF" })
		face:blend(render())

		reel[#reel + 1] = face
	end

	local viewer_args = {
		args.id,
		"--stdout",
		"--time",
		0,
		"--skin",
		args.skin or "-",
	}

	local frame = stream("nikke-viewer", {
		width = base.width,
		height = base.height,
		color_space = "srgb",
		alpha = "premultiplied",
		args = viewer_args,
	})()
	local output = base:clone()

	local left = rectangle({ x = 150, y = 220, size = { 300, 350 } })
	local right = rectangle({ x = 1220, y = 220, size = { 300, 350 } })
	local offset_x = 500

	if frame:coverage_in(left) < frame:coverage_in(right) then
		offset_x = -500
	end

	local face = stream("nikke-viewer", {
		width = base.width,
		height = base.height,
		color_space = "srgb",
		alpha = "premultiplied",
		args = {
			"--face",
			"--zoom",
			2,
			"--offset-x",
			offset_x * scale,
			table.unpack(viewer_args),
		},
	})()

	local tint = frame:vivid_in(rectangle({ size = frame.size }))

	do
		local tint = tint:to_oklch()

		tint.c = math.min(tint.c, 0.04)
		tint.l = math.min(tint.l, 0.2)

		output:blend(face)
		output:monochrome(tint)

		local fade =
			gradient(180):stop(0.0, tint:with_alpha(0.5)):stop(1.0, tint)

		output:fill(rectangle({ size = output.size }), fade)
	end

	output:blend(mask)

	if args.manufacturer ~= nil then
		manufacturer.render(
			output,
			args.manufacturer,
			{ x = 25, y = -height * (1 - 0.72) - 80 }
		)
	end

	output:blend(frame)
	-- output:fill(left, "#000000")
	-- output:fill(right, "#000000")

	logo.reset()
	copyright.reset()

	logo.render(output, { x = -75, y = 75 })
	copyright.render(output, { x = 50, y = height - 15 })

	title.render(output, {
		title = args.title,
		subtitle = args.subtitle,
		y = height * 0.72,
		tint = tint,
	})

	for i, face in ipairs(reel) do
		local bounds = rectangle({
			x = width - face.width - 75,
			y = height * 3 / 7 + (face.height + 50) * (i - 1),
			size = face.size,
		})

		local tint = tint:to_oklch()
		tint.l = 0.2

		output:fill(bounds:padded(1 / scale), tint:with_alpha(0.7))

		output:blend(face, {
			at = bounds,
		})
	end

	yield(output)
end

return profile
