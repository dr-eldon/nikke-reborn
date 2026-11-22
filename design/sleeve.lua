local logo = require("nikke/logo")
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
		"title",
		"background",
		"model",
		"animation",
		"time",
		"x",
		"portrait",
	},
	render = function(args)
		-- args.title = "Neon"
		-- args.background = "nikke-room"
		-- args.model = "c014"
		-- args.animation = "action"
		-- args.time = 1
		-- args.x = -20
		-- args.portrait = "shy"

		local background =
			image("../assets/images/backgrounds/" .. args.background .. ".png")

		background:resize({
			width = front.width,
			height = front.height,
			mode = "cover",
		})

		-- Front
		local base = base:clone()

		local character = stream("nikke-viewer", {
			width = front.width,
			height = front.height,
			color_space = "srgb",
			alpha = "premultiplied",
			args = {
				"--stdout",
				"--skin",
				args.skin or "-",
				"--animation",
				args.animation or "-",
				"--time",
				args.time or 0,
				"--offset-x",
				args.x or 0,
				"--half-body",
				args.model,
			},
		})()

		local tint = character
			:vivid_in(rectangle({ size = { front.width, front.height } }))
			:to_oklch()

		tint.c = 0.1

		background:monochrome(tint)
		base:blend(background, { at = front })
		base:blend(character, { at = front })

		-- Label
		tint.c = 0.2
		base:fill(label, tint)
		base:blend(hex, { at = label })

		local inset = label.width / 20
		local invert = logo.glowing(base, {
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

		local title =
			text(args.title:upper(), { font = aire, size = label.height * 0.3 })
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

		local face = stream("nikke-viewer", {
			width = label.height * 0.4,
			height = label.height * 0.4,
			color_space = "srgb",
			alpha = "premultiplied",
			args = {
				"--stdout",
				"--skin",
				args.skin or "-",
				"--animation",
				args.portrait or "-",
				"--portrait",
				args.model,
			},
		})()

		local face_bounds = rectangle({
			x = title.x,
			y = label.y + inset,
			size = face.size,
		})

		base:fill(face_bounds:padded(1 / scale), "#000000")
		base:fill(face_bounds, "#FFFFFF")
		base:blend(face, { at = face_bounds })

		yield(base)
	end,
}
