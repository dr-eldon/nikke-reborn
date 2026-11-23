local copyright = require("nikke/copyright")
local logo = require("nikke/logo")
local title = require("nikke/title")

local aire = font("../fonts/AireExterior.ttf")
local oswald = font("../fonts/Oswald.ttf")

local mask = image("../assets/images/CardSleeve_Material_Mask.png")
local base = image("../assets/images/CardSleeve_Material_Clear.png")
local hex = image("../assets/images/designs/Card_Sleeve_Label.png")

local width = 2048
local height = 2048

mask:resize({ width = width, height = height, filter = "nearest" })
base:resize({ width = width, height = height })

local label = mask:detect("#FF0000")()
local front = mask:detect("#00FF00")()

hex:resize({ width = label.width, height = label.height })

return {
	arguments = {
		"id",
		"title",
		"background",
		"skin",
		"variant",
		"animation",
		"time",
		"offset_x",
		"portrait",
		"focus",
		"zoom",
	},
	render = function(args)
		-- args.id = "c382"
		-- args.title = "Leona"
		-- args.background = "kitchen"
		-- args.variant = "sc"
		-- args.animation = "main"
		-- args.focus = "full-body"
		-- args.time = 2.8
		-- args.portrait = "chu2"

		local inset = math.floor(label.width / 20)

		local background =
			image("../assets/images/backgrounds/" .. args.background .. ".png")

		background:resize({
			width = front.width,
			height = front.height,
			mode = "cover",
		})
		background:autocontrast()

		local character = stream("nikke-viewer", {
			width = front.width,
			height = front.height,
			color_space = "srgb",
			alpha = "premultiplied",
			args = {
				"--stdout",
				"--skin",
				args.skin or "-",
				"--time",
				0,
				args.id,
			},
		})()

		local tint = character
			:vivid_in(rectangle({ size = { front.width, front.height } }))
			:to_oklch()

		tint.a = 1.0

		-- Front
		local base = base:clone()

		local character = stream("nikke-viewer", {
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
				"--offset-x",
				(args.offset_x or 0) * scale,
				"--" .. (args.focus or "half-body"),
				"--zoom",
				args.zoom or 1.0,
				args.id,
			},
		})()

		-- background:monochrome(tint)

		-- local black = srgb(0, 0, 0)

		-- local fade = gradient(180)
		-- 	:stop(0.0, black:with_alpha(0.3))
		-- 	:stop(1.0, black:with_alpha(0.8))

		-- background:fill(rectangle({ size = background.size }), fade)

		base:blend(background, { at = front })
		base:blend(character, { at = front })

		copyright.reset()
		copyright.render(base, {
			x = front.x + inset - 20,
			y = front.y + front.height - inset + 60,
			size = 10,
		})

		-- Label
		if tint.c > 0.02 then
			tint.c = 0.2
		end

		base:fill(label, tint)
		base:blend(hex, { at = label })

		local invert = logo.glowing(base, {
			flat = true,
			width = label.width / 4,
			position = function(width, height)
				return {
					label.x + label.width - width - inset - 60,
					label.y + inset,
				}
			end,
		})

		local subtitle = text(
			"100 PERFECT FIT SLEEVES",
			{ font = oswald, size = label.height * 0.10, weight = 600 }
		)

		local title = text(args.title:upper(), {
			font = aire,
			size = title.size(label.height * 0.3, 17, args.title),
		})
		local size = text(
			"65x90mm",
			{ font = oswald, size = label.height * 0.10, weight = 600 }
		)

		local text_color = "#000000"

		if invert then
			tint.l = 0.7
		else
			text_color = "#FFFFFF"
			tint.l = 0.5
		end

		subtitle:translate({
			x = label.x + inset,
			y = label.y + label.height - subtitle.height - inset / 2,
		})
		size:translate({
			x = label.x + label.width - size.width - inset - 60,
			y = subtitle.y,
		})
		title:translate({
			x = subtitle.x,
			y = subtitle.y - title.height - inset / 2,
		})

		base:fill(title, tint)
		title:translate({ x = -5, y = -5 })
		base:fill(title, text_color)

		base:fill(subtitle, text_color)
		base:fill(size, text_color)

		do
			local size = math.floor(label.height * 0.4 * scale) / scale
			local face = stream("nikke-viewer", {
				width = size,
				height = size,
				color_space = "srgb",
				alpha = "premultiplied",
				args = {
					"--stdout",
					"--portrait",
					"--time",
					0,
					"--skin",
					args.skin or "-",
					"--animation",
					args.portrait or "-",
					args.id,
				},
			})()

			local face_bounds = rectangle({
				x = math.floor(title.x),
				y = math.floor(label.y + inset),
				size = face.size,
			})

			base:fill(face_bounds:padded(2), "#000000")
			base:fill(face_bounds, "#FFFFFF")
			base:blend(face, { at = face_bounds })
		end

		yield(base)
	end,
}
