local character = require("nikke.character")
local copyright = require("nikke.copyright")
local logo = require("nikke.logo")

local standard = {}
local width = 1640
local height = 2048
local cache = {}

standard.arguments = {
	"id",
	"background",
	"variant",
	"skin",
	"animation",
	"time",
	"focus",
	"monochrome",
}

function standard.render(args)
	if args.background ~= nil and cache[args.background] == nil then
		local base =
			image("../assets/images/backgrounds/" .. args.background .. ".png")

		base:autocontrast()
		base:resize({ width = width, height = height, mode = "cover" })
		base:convert("srgb")

		cache[args.background] = base
	end

	local base

	if args.background == nil then
		base = blank({
			width = width,
			height = height,
			color = "#000000",
			color_space = "srgb",
		})
	else
		base = cache[args.background]
	end

	local variant = args.variant or "fb"

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

	local i = 0

	logo.reset()
	copyright.reset()

	for frame in frames do
		i = i + 1

		if i == 1 and args.monochrome then
			local color = character.accent(args.id, args.skin)

			base = base:clone()
			base:monochrome(color)
		end

		local output = base:clone()
		output:blend(frame)

		logo.render(output, { x = -75, y = -75 })
		copyright.render(output, { x = 50, y = height - 15 })

		yield(output)
	end
end

return standard
