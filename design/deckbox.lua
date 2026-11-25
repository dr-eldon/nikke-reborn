local logo = require("nikke/logo")

local width = 2048
local height = 2048

local mask = image("../assets/images/DeckBox_Material_Mask.png")
local leather = image("../assets/images/designs/Leather_Mask.png")

mask:resize({ width = width, height = height, filter = "nearest" })
leather:resize({ width = width, height = height })

local front = mask:detect("#FF0000")()
local bottom = mask:detect("#0000FF")()

local sides = mask:detect("#00FF00")
local left = sides()
local right = sides()

return {
	arguments = {
		"id",
		"skin",
		"variant",
		"animation",
		"time",
		"focus",
		"zoom",
		"offset_x",
		"color",
	},
	render = function(args)
		local render = stream("nikke-viewer", {
			width = front.width,
			height = front.height,
			color_space = "srgb",
			alpha = "premultiplied",
			args = {
				"--stdout",
				"--variant",
				args.variant or "-",
				"--skin",
				args.skin or "-",
				"--animation",
				args.animation or "-",
				"--time",
				args.time or 0,
				"--zoom",
				args.zoom or 1,
				"--" .. (args.focus or "half-body"),
				"--offset-x",
				(args.offset_x or 0) * scale,
				args.id,
			},
		})()

		local tint

		if args.color == nil then
			tint = render:vivid_in(rectangle({ size = render.size })):to_oklch()
		else
			tint = color(args.color):to_oklch()
		end

		tint.c = tint.c * 1.3
		tint.l = tint.l * 0.9

		local material = blank({ width = width, height = height, color = tint })

		local darker = tint:clone()
		darker.l = darker.l * 0.5
		material:fill(bottom, darker)

		material:blend(render, { at = front })

		logo.glowing(material, {
			width = left.width * 0.6,
			flat = true,
			position = function(width, height)
				return {
					left.x + (left.width - width) / 2,
					left.y + (left.height - height) / 2,
				}
			end,
		})

		logo.glowing(material, {
			width = right.width * 0.6,
			flat = true,
			position = function(width, height)
				return {
					right.x + (right.width - width) / 2,
					right.y + (right.height - height) / 2,
				}
			end,
		})

		material:blend(leather)

		yield(material)
	end,
}
