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
	"animation",
	"time",
}

function standard.render(args)
	if args.background ~= nil and cache[args.background] == nil then
		local base =
			image("../assets/images/backgrounds/" .. args.background .. ".png")

		base:autocontrast()
		base:resize({ width = width, height = height, mode = "cover" })

		cache[args.background] = base
	end

	local base

	if args.background == nil then
		base = blank({ width = width, height = height, color = "#000000" })
	else
		base = cache[args.background]
	end

	local variant = args.variant or "fb"
	local focus = variant == "fb" and "--half-body" or "--full-body"

	local character = stream("nikke-viewer", base.width, base.height, {
		"--stdout",
		"--variant",
		variant,
		focus,
		"--animation",
		args.animation or "-",
		"--time",
		args.time or "-",
		args.id,
	})

	for frame in character do
		local output = base:clone()
		output:blend(frame)

		logo.render(output, { x = -75, y = -75 })
		copyright.render(output, { x = 50, y = height - 15 })

		yield(output)
	end
end

return standard
