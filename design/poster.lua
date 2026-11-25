local width = 2048
local height = 2048

local mask_square = image("../assets/images/Poster_Square_Material.png")
local mask_rectangle = image("../assets/images/Poster_Rectangle_Material.png")

mask_square:resize({ width = width, height = height, filter = "nearest" })
mask_rectangle:resize({ width = width, height = height, filter = "nearest" })

return {
	arguments = { "file", "aspect" },
	render = function(args)
		local art = image("../assets/gallery/" .. args.file .. ".png")
		local aspect = args.aspect:lower()

		if aspect == "square" then
			local base = mask_square:clone()
			local region = base:detect("#FF0000")()

			art:resize({
				width = region.width,
				height = region.height,
				mode = "cover",
			})

			base:blend(art, { at = region })
			yield(base)
		else
			local base = mask_rectangle:clone()
			local region = base:detect("#FF0000")()

			if aspect == "landscape" then
				art:rotate(90)
			end

			art:resize({
				width = region.width,
				height = region.height,
				mode = "cover",
			})

			base:blend(art, { at = region })
			yield(base)
		end
	end,
}
