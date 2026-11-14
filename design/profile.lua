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
	"animation",
	"reel",
}

function profile.render(args)
	if cache[args.background] == nil then
		local base =
			image("../assets/images/backgrounds/" .. args.background .. ".png")
		local tint = base:dominant_in(rectangle({ size = base.size }))

		base:autocontrast()
		base:resize({ width = width, height = height, mode = "cover" })
		base:monochrome(tint)

		cache[args.background] = { base, tint }
	end

	local base, tint = table.unpack(cache[args.background])

	local reel = {}

	for expression in string.gmatch(args.reel, "([^,]+)") do
		local size = math.floor(base.width / 7)

		local render = stream("nikke-viewer", size, size, {
			args.id,
			"--stdout",
			"--portrait",
			"--animation",
			expression,
			"--time",
			0,
		})

		local face = blank({ width = size, height = size, color = "#FFFFFF" })
		face:blend(render())

		reel[#reel + 1] = face
	end

	local viewer_args = { args.id, "--stdout", "--time", 0 }

	if args.animation ~= nil then
		viewer_args[#viewer_args + 1] = "--animation"
		viewer_args[#viewer_args + 1] = args.animation
	end

	local frame = stream("nikke-viewer", base.width, base.height, viewer_args)()
	local output = base:clone()

	local left = rectangle({ x = 150, y = 220, size = { 300, 350 } })
	local right = rectangle({ x = 1220, y = 220, size = { 300, 350 } })
	local offset_x = 500

	if frame:coverage_in(left) < frame:coverage_in(right) then
		offset_x = -500
	end

	local face = stream("nikke-viewer", base.width, base.height, {
		"--face",
		"--zoom",
		2,
		"--offset-x",
		offset_x * scale,
		table.unpack(viewer_args),
	})()
	face:monochrome(tint)
	output:blend(face)

	local fade = gradient(180):stop(0.3, tint:with_alpha(0.85)):stop(1.0, tint)
	output:fill(rectangle({ size = output.size }), fade)

	output:blend(mask)
	output:blend(frame)
	-- output:fill(left, "#000000")
	-- output:fill(right, "#000000")

	logo.render(output, { x = -75, y = 75 })
	copyright.render(output, { x = 50, y = height - 15 })

	title.render(output, {
		title = args.title,
		subtitle = args.subtitle,
		y = height * 0.72,
		tint = tint,
	})

	if args.manufacturer ~= nil then
		manufacturer.render(
			output,
			args.manufacturer,
			{ x = 50, y = -height * (1 - 0.72) - 80 }
		)
	end

	for i, face in ipairs(reel) do
		local bounds = rectangle({
			x = width - face.width - 75,
			y = height * 3 / 7 + (face.height + 50) * (i - 1),
			size = face.size,
		})

		output:fill(bounds:padded(1), tint)

		output:blend(face, {
			at = bounds,
		})
	end

	yield(output)
end

return profile
