local nikke_logo = require("nikke/logo")

local width = 2048
local height = 2048

local material = image("../assets/images/CardBox_Material.png")
material:resize({ width = width, height = height, filter = "nearest" })
material:convert("srgb")

local side = material:detect("#00FF00")()
local front = material:detect("#0000FF")()
local top = material:detect("#FF0000")()

return {
	arguments = { "background", "characters", "logo" },
	render = function(args)
		-- args.background = "sky-night"
		-- args.background = "beach-day"
		-- args.characters = {
		-- 	{ id = "c010", animation = "action", time = 1.247 },
		-- 	{ id = "c011" },
		-- 	{ id = "c013", animation = "action", time = 2 },
		-- { id = "c353", animation = "action", time = 3 },
		-- { id = "c142_01", animation = "action", time = 1.34 },
		-- { id = "c014", animation = "action", time = 4.1 },
		-- }
		-- args.logo = "BlueWaterIsland"

		local background = image(
			"../assets/images/backgrounds/"
				.. (args.background.id or args.background)
				.. ".png"
		)
		background:autocontrast()
		background:convert("srgb")

		local logo
		if args.logo ~= nil then
			logo = image("../assets/images/logos/" .. args.logo .. ".png")
			logo:convert("srgb")
		end

		local nikke_logo_width = front.width / 6
		local padding = nikke_logo_width / 5

		-- Side
		local base = background:clone()
		base:resize({
			width = side.width,
			height = side.height,
			mode = "cover",
			align_y = args.background.side and args.background.side.align_y
				or "bottom",
		})
		material:blend(base, { at = side })

		if logo == nil then
			nikke_logo.glowing(material, {
				height = side.height / 3,
				position = function(width, height)
					return {
						side.x + (side.width - width) / 2,
						side.y + (side.height - height) / 2,
					}
				end,
			})
		else
			local logo = logo:clone()
			logo:resize({ width = side.width * 0.8 })
			material:blend(logo, {
				at = rectangle({
					x = side.x + (side.width - logo.width) / 2,
					y = side.y + (side.height - logo.height) / 2,
					size = logo.size,
				}),
			})

			nikke_logo.glowing(material, {
				width = nikke_logo_width,
				position = function(width, height)
					return {
						side.x + (side.width - width) / 2,
						side.y + side.height - height - padding,
					}
				end,
			})
		end

		-- Front
		local base = background:clone()
		base:resize({
			width = front.width,
			height = front.height,
			mode = "cover",
			align_y = args.background.front and args.background.front.align_y
				or "bottom",
		})
		material:blend(base, { at = front })

		for i = #args.characters, 1, -1 do
			local character = args.characters[i]
			local offset = 0
			local zoom = character.zoom or 1.0
			local at = front

			if i > 1 then
				offset = (-1) ^ (i % 2)
					* (front.width * 2 / 7 + (character.x or 0))

				offset = -math.floor(offset + 0.5)
				zoom = zoom - 0.25 * math.floor(i / 2)

				local translate = math.floor(i / 2) * front.height / 10

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

		if logo ~= nil then
			local logo = logo:clone()
			logo:resize({ width = 0.4 * front.width })
			material:blend(logo, {
				at = rectangle({
					x = front.x + (front.width - logo.width) / 2,
					y = front.y + front.height - logo.height - front.width / 30,
					size = logo.size,
				}),
			})
		end

		nikke_logo.glowing(material, {
			width = nikke_logo_width,
			position = function(_width, _height)
				return { front.x + padding, front.y + padding }
			end,
		})

		-- Top
		local base = background:clone()
		base:resize({
			width = top.width,
			height = top.height,
			mode = "cover",
			align_y = args.background.top and args.background.top.align_y
				or "center",
		})
		material:blend(base, { at = top })

		if logo == nil then
			nikke_logo.glowing(material, {
				height = top.width / 4,
				position = function(width, height)
					return {
						top.x + (top.width - width) / 2,
						top.y + (top.height - height) / 2,
					}
				end,
			})
		else
			logo:resize({ width = top.width * 0.7 })
			material:blend(logo, {
				at = rectangle({
					x = top.x + (top.width - logo.width) / 2,
					y = top.y + (top.height - logo.height) / 2,
					size = logo.size,
				}),
			})

			nikke_logo.glowing(material, {
				width = nikke_logo_width,
				position = function(_width, _height)
					return { top.x + padding, top.y + padding }
				end,
			})
		end

		yield(material)
	end,
}
