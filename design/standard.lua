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

standard.arguments = {
	"id",
	"background",
	"manufacturer",
	"title",
	"subtitle",
	"variant",
	"animation",
	"time",
}

function standard.render(args)
	if cache[args.background] == nil then
		local base =
			image("../assets/images/backgrounds/" .. args.background .. ".png")
		local tint = base:dominant_in(rectangle({ size = base.size }))

		base:autocontrast()
		base:resize({ width = width, height = height, mode = "cover" })
		base:blend(mask)
		base:convert("srgb")

		cache[args.background] = { base, tint }
	end

	local base, tint = table.unpack(cache[args.background])
	local variant = args.variant or "fb"
	local focus = variant == "fb" and "--half-body" or "--full-body"

	local character = stream("nikke-viewer", {
		width = base.width,
		height = base.height,
		color_space = "srgb",
		alpha = "premultiplied",
		args = {
			"--stdout",
			"--variant",
			variant,
			focus,
			"--animation",
			args.animation or "-",
			"--time",
			args.time or "-",
			args.id,
		},
	})

	logo.reset()
	copyright.reset()

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
