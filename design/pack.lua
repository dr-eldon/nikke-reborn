local nikke_logo = require("nikke/logo")

local width = 2048
local height = 2048

local material = image("../assets/images/CardPack_Material.png")
material:resize({ width = width, height = height, filter = "nearest" })
material:convert("srgb")

local masks = material:detect("#0000FF")

local left = masks()
local right = masks()

return {
	arguments = { "background", "characters", "logo" },
	render = function(args)
		-- args.background = "sky-night"
		-- args.background = "beach-day"
		-- args.characters = {
		-- { id = "c010", animation = "action", time = 1.247 },
		-- { id = "c011" },
		-- { id = "c013", animation = "action", time = 2 },
		-- { id = "c353", animation = "action", time = 3 },
		-- { id = "c142_01", animation = "action", time = 1.34 },
		-- { id = "c014", animation = "action", time = 4.1 },
		-- }
		-- args.logo = "BlueWaterIsland"

		local padding = 100

		local background = image(
			"../assets/images/backgrounds/"
				.. (args.background.id or args.background)
				.. ".png"
		)

		local logo
		if args.logo ~= nil then
			logo = image("../assets/images/logos/" .. args.logo .. ".png")
			logo:convert("srgb")
		end

		do
			local background = background:clone()
			background:resize({
				width = left.width,
				height = left.height,
				mode = "cover",
			})

			material:blend(background, { at = left })
		end

		do
			background:resize({
				width = right.width,
				height = right.height,
				mode = "cover",
			})

			material:blend(background, { at = right })

			for i = #args.characters, 1, -1 do
				local character = args.characters[i]
				local offset = 0
				local zoom = 0.8 * (character.zoom or 1.0)
				local at = right
				local translate = at.height / 7

				if i > 1 then
					offset = (-1) ^ (i % 2)
						* (right.width * 2 / 6 + (character.x or 0))

					offset = -math.floor(offset + 0.5)
					zoom = zoom - 0.35 * math.floor(i / 2)

					translate = translate + math.floor(i / 2) * right.height / 9
				end

				at = rectangle({
					x = at.x,
					y = at.y + translate,
					size = { at.width, at.height - translate },
				})

				local render = stream("nikke-viewer", {
					width = right.width,
					height = right.height,
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

			nikke_logo.glowing(material, {
				width = right.width * 0.65,
				position = function(width, _height)
					return {
						right.x + (right.width - width) / 2,
						right.y + padding,
					}
				end,
			})

			if logo ~= nil then
				logo:resize({ width = right.width * 0.7 })
				material:blend(logo, {
					at = rectangle({
						x = right.x + (right.width - logo.width) / 2,
						y = right.y
							+ right.height
							- logo.height
							- padding / 1.5,
						size = logo.size,
					}),
					color_space = "srgb",
				})
			end
		end

		yield(material)
	end,
}
