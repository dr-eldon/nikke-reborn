local logo = require("nikke/logo")

local width = 2048
local height = 2048

local mask = image("../assets/images/DeckBox_Material_Mask.png")
local leather = image("../assets/images/designs/Leather_Mask.png")
local leather_low = image("../assets/images/designs/Leather_Mask_low.png")

mask:resize({ width = width, height = height, filter = "nearest" })
leather:resize({ width = width, height = height })
leather_low:resize({ width = width, height = height })

local front = mask:detect("#FF0000")()
local bottom = mask:detect("#0000FF")

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
		"offset_y",
		"color",
	},
	render = function(args)
		-- A2
		-- args = {
		-- 	id = "c811",
		-- 	variant = "sc",
		-- 	animation = "idle",
		-- 	time = 0,
		-- 	focus = "full-body",
		-- 	-- zoom = 1.1,
		-- 	-- offset_x = 40,
		-- 	-- offset_y = -20,
		-- 	color = "#444444",
		-- }
		-- Marciana
		-- args = {
		-- 	id = "c321",
		-- 	variant = "sc",
		-- 	animation = "idle",
		-- 	time = 3.7,
		-- 	focus = "full-body",
		-- 	zoom = 1.2,
		-- 	offset_x = 50,
		-- 	offset_y = -100,
		-- 	color = "#FFFFFF",
		-- }
		-- Naga
		-- args = {
		-- 	id = "c450",
		-- 	variant = "sc",
		-- 	animation = "idle",
		-- 	time = 3,
		-- 	focus = "half-body",
		-- 	zoom = 1.2,
		-- 	-- offset_x = 50,
		-- 	offset_y = -10,
		-- 	-- color = "#FFFFFF",
		-- 	color = "#544c99",
		-- }
		-- Crown
		-- args = {
		-- 	id = "c330",
		-- 	variant = "sc",
		-- 	animation = "idle",
		-- 	time = 0,
		-- 	focus = "full-body",
		-- 	zoom = 1.2,
		-- 	offset_y = 30,
		-- 	offset_x = 30,
		-- 	color = "#FFFFFF",
		-- }
		-- Makima
		-- args = {
		-- 	id = "c800",
		-- 	variant = "sc",
		-- 	animation = "main",
		-- 	time = 2.14,
		-- 	focus = "full-body",
		-- 	zoom = 1.03,
		-- 	offset_x = 80,
		-- 	offset_y = -110,
		-- }
		-- Dorothy
		-- args = {
		-- 	id = "c233_01",
		-- 	variant = "fb",
		-- 	animation = "think",
		-- 	time = 0,
		-- 	focus = "half-body",
		-- }
		-- Scarlet: Black Shadow
		-- args = {
		-- 	id = "c225",
		-- 	variant = "sc",
		-- 	animation = "skillcut_1",
		-- 	time = 2.45,
		-- 	focus = "full-body",
		-- 	offset_x = -80,
		-- 	offset_y = -5,
		-- 	color = "#222222",
		-- }

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
				"--offset-y",
				(args.offset_y or 0) * scale,
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

		if tint.l < 1.0 then
			tint.l = tint.l * 0.9
		end

		local material = blank({ width = width, height = height, color = tint })

		local darker = tint:clone()
		darker.l = darker.l * 0.5

		for region in bottom do
			material:fill(region, darker)
		end

		material:blend(render, { at = front })

		local shadow_h = gradient(90)
			:stop(0.0, color("#000000"):with_alpha(0.4))
			:stop(0.1, color("#000000"):with_alpha(0))
			:stop(0.9, color("#000000"):with_alpha(0))
			:stop(1.0, color("#000000"):with_alpha(0.4))

		local shadow_v = gradient(0)
			:stop(0.0, color("#000000"):with_alpha(0.3))
			:stop(0.05, color("#000000"):with_alpha(0))
			:stop(0.95, color("#000000"):with_alpha(0))
			:stop(1.0, color("#000000"):with_alpha(0.3))

		material:fill(left, shadow_h)
		material:fill(left, shadow_v)

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

		material:fill(right, shadow_h)
		material:fill(right, shadow_v)

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

		if scale < 1.0 then
			material:blend(leather_low)
		else
			material:blend(leather)
		end

		yield(material)
	end,
}
