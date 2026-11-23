local width = 1024
local height = 1024

return {
	arguments = { "file" },
	render = function(args)
		local art = image("../assets/gallery/" .. args.file .. ".png")

		if art.width > art.height then
			art:resize({ width = width })
		else
			art:resize({ height = height })
		end

		local base = blank({ width = width, height = height })
		base:blend(art, {
			at = rectangle({
				x = (width - art.width) / 2,
				y = (height - art.height) / 2,
				size = art.size,
			}),
		})

		yield(base)
	end,
}
