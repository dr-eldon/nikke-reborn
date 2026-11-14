local copyright = require("nikke.copyright")
local logo = require("nikke.logo")
local manufacturer = require("nikke.manufacturer")
local title = require("nikke.title")

local standard = {}
local width = 1640
local height = 2048
local cache = {}

local mask = image("../assets/images/designs/Card_Mask_Standard.png")
mask:resize({ width = width, height = height })

standard.arguments =
	{ "id", "background", "manufacturer", "title", "subtitle", "animation", "time" }

function standard.render(args)
	if cache[args.background] == nil then
		local base = image("../assets/images/backgrounds/" .. args.background .. ".png")
		local tint = base:dominant_in(rectangle({ size = base.size }))

		base:autocontrast()
		base:resize({ width = width, height = height, mode = "cover" })
		base:blend(mask)

		cache[args.background] = { base, tint }
	end

	local base, tint = table.unpack(cache[args.background])
	local viewer_args = { "--half-body", "--stdout", args.id }

	if args.animation ~= nil then
		viewer_args[#viewer_args + 1] = "--animation"
		viewer_args[#viewer_args + 1] = args.animation
	end

	if args.time ~= nil then
		viewer_args[#viewer_args + 1] = "--time"
		viewer_args[#viewer_args + 1] = args.time
	end

	local character = stream("nikke-viewer", base.width, base.height, viewer_args)

	for frame in character do
		local output = base:clone()
		output:blend(frame)

		logo.render(output, { x = -75, y = -75 })
		copyright.render(output, { x = 50, y = height - 15 })

		title.render(output, {
			title = args.title,
			subtitle = args.subtitle,
			y = height * 0.72,
			tint = tint,
		})

		if args.manufacturer ~= nil then
			manufacturer.render(output, args.manufacturer, { x = -75, y = 75 })
		end

		yield(output)
	end
end

return standard
