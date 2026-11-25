local character = require("nikke.character")
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
	"skin",
	"animation",
	"time",
	"focus",
	"monochrome",
}

function standard.render(args)
	local key = { args.background, args.monochrome and args.id }

	if cache[key] == nil then
		local base =
			image("../assets/images/backgrounds/" .. args.background .. ".png")

		base:autocontrast()
		base:resize({ width = width, height = height, mode = "cover" })

		local tint = character.accent(args.id, args.skin)

		if args.monochrome then
			base:monochrome(tint)
		end

		base:blend(mask)
		base:convert("srgb")

		cache[key] = { base, tint }
	end

	local variant = args.variant or "fb"
	local base, tint = table.unpack(cache[key])

	local frames = stream("nikke-viewer", {
		width = base.width,
		height = base.height,
		color_space = "srgb",
		alpha = "premultiplied",
		args = {
			"--stdout",
			"--variant",
			variant,
			"--skin",
			args.skin or "-",
			"--animation",
			args.animation or "-",
			"--time",
			args.time or "-",
			"--" .. args.focus,
			args.id,
		},
	})

	logo.reset()
	copyright.reset()

	local i = 0

	for frame in frames do
		local output = base:clone()

		if args.manufacturer ~= nil then
			manufacturer.render(output, args.manufacturer, { x = -75, y = 75 })
		end

		output:blend(frame)

		logo.render(output, { x = -75, y = -75 })
		copyright.render(output, { x = 50, y = height - 15 })

		title.render(output, {
			title = args.title,
			subtitle = args.subtitle,
			y = height * 0.72,
			tint = tint,
		})

		yield(output)
	end
end

return standard
