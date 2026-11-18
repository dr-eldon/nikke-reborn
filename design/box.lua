local logo = require("nikke/logo")

local width = 2048
local height = 2048

local material = image("../assets/images/CardBox_Material.png")
material:resize({ width = width, height = height, filter = "nearest" })
material:convert("srgb")

local side = material:detect("#00FF00")()
local front = material:detect("#0000FF")()
local top = material:detect("#FF0000")()

return {
	arguments = { "background" },
	render = function(args)
		args.characters = {
			{ id = "c010", animation = "action", time = 1.247 },
			{ id = "c011" },
			{ id = "c013", animation = "action", time = 2, x = 40 },
		}

		local background =
			image("../assets/images/backgrounds/" .. args.background .. ".png")
		background:autocontrast()
		background:convert("srgb")

		-- Side
		local base = background:clone()
		base:resize({
			width = side.width,
			height = side.height,
			mode = "cover",
			align_y = "bottom",
		})
		material:blend(base, { at = side })

		logo.glowing(material, {
			height = side.height / 3,
			position = function(width, height)
				return {
					side.x + (side.width - width) / 2,
					side.y + (side.height - height) / 2,
				}
			end,
		})

		-- Front
		local base = background:clone()
		base:resize({
			width = front.width,
			height = front.height,
			mode = "cover",
			align_y = "bottom",
		})
		material:blend(base, { at = front })

		for i = #args.characters, 1, -1 do
			local character = args.characters[i]
			local offset = 0
			local zoom = 0.9
			local at = front

			if i > 1 then
				offset = (-1) ^ (i % 2)
					* (front.width * 2 / 7 + (character.x or 0))

				offset = -math.floor(offset + 0.5)
				zoom = zoom - 0.15 * math.floor(i / 2)

				local translate = math.floor(i / 2) * front.height / 8

				at = rectangle({
					x = at.x,
					y = at.y + translate,
					size = { at.width, at.height - translate },
				})
			end

			local render = stream("nikke-viewer", {
				width = front.width,
				height = front.height,
				color_space = "srgb",
				alpha = "premultiplied",
				args = {
					character.id,
					"--stdout",
					"--half-body",
					"--animation",
					character.animation or "-",
					"--time",
					character.time or 0,
					"--zoom",
					zoom,
					"--offset-x",
					offset * scale,
				},
			})()

			material:blend(render, { at = at })
		end

		logo.glowing(material, {
			height = front.height / 7,
			position = function(_width, _height)
				return { front.x + front.width / 30, front.y + front.width / 30 }
			end,
		})

		-- Top
		local base = background:clone()
		base:resize({
			width = top.width,
			height = top.height,
			mode = "cover",
		})
		material:blend(base, { at = top })

		logo.glowing(material, {
			height = top.width / 4,
			position = function(width, height)
				return {
					top.x + (top.width - width) / 2,
					top.y + (top.height - height) / 2,
				}
			end,
		})

		yield(material)
	end,
}
