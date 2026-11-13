local title = {}

local aire_exterior = font("../../fonts/AireExterior.ttf")
local chocolate = font("../../fonts/ChocolateClassicalSans-Regular.ttf")

function title.render(output, args)
	local title = text(args.title:upper(), {
		font = aire_exterior,
		size = size(150, 10, args.title),
		weight = 700,
		x = 50,
		y = args.y,
	})

	local arrow = text(
		"↖",
		{ font = chocolate, size = size(50, 15, args.title), x = title.x + title.width, y = title.y + title.height }
	)
	arrow:translate({ x = 25, y = -arrow.height })

	local title_bounds = title.bounds:padded({ 20, 45 + arrow.width })
	local title_box = path()
	title_box:move_to({ x = title_bounds.x, y = title_bounds.y })
	title_box:line_to({ x = title_bounds.x + title_bounds.width - title_bounds.height / 3, y = title_bounds.y })
	title_box:line_to({ x = title_bounds.x + title_bounds.width, y = title_bounds.y + title_bounds.height / 3 })
	title_box:line_to({ x = title_bounds.x + title_bounds.width, y = title_bounds.y + title_bounds.height })
	title_box:line_to({ x = title_bounds.x, y = title_bounds.y + title_bounds.height })
	title_box:close()

	output:fill(title_box, "#333333")
	output:fill(title, "#FFFFFF")
	output:fill(arrow, "#FFFFFF")

	local bar = parallelogram(200, 25, 25)
	bar:translate({ x = -40, y = title_bounds.y - 35 })

	local square = 25
	local spacing = square / 2
	local square_1 = parallelogram(square, 25, 25)
	square_1:translate({ x = -40 + 200 + spacing, y = title_bounds.y - 35 })

	local square_2 = parallelogram(square, 25, 25)
	square_2:translate({ x = -40 + 200 + square + 2 * spacing, y = title_bounds.y - 35 })

	local square_3 = parallelogram(square, 25, 25)
	square_3:translate({ x = -40 + 200 + 2 * square + 3 * spacing, y = title_bounds.y - 35 })

	output:fill(bar, "#333333")
	output:fill(square_1, "#333333")
	output:fill(square_2, "#333333")
	output:fill(square_3, "#333333")

	if args.subtitle ~= nil then
		local subtitle = text(args.subtitle:upper(), {
			font = aire_exterior,
			size = size(50, 30, args.subtitle),
			weight = 700,
			x = 50,
			y = title_bounds.y + title_bounds.height + spacing,
		})

		local subtitle_bounds = subtitle.bounds:padded({ top = spacing, bottom = spacing, left = 50, right = 50 })
		local subtitle_box = path()
		subtitle_box:move_to({ x = subtitle_bounds.x, y = subtitle_bounds.y })
		subtitle_box:line_to({
			x = subtitle_bounds.x + subtitle_bounds.width,
			y = subtitle_bounds.y,
		})
		subtitle_box:line_to({
			x = subtitle_bounds.x + subtitle_bounds.width,
			y = subtitle_bounds.y + 2 * subtitle_bounds.height / 3,
		})
		subtitle_box:line_to({
			x = subtitle_bounds.x + subtitle_bounds.width - subtitle_bounds.height / 3,
			y = subtitle_bounds.y + subtitle_bounds.height,
		})
		subtitle_box:line_to({ x = subtitle_bounds.x, y = subtitle_bounds.y + subtitle_bounds.height })
		subtitle_box:close()

		local tint = args.tint:to_oklch()
		tint.c = 0.2
		tint.l = 0.5

		output:fill(subtitle_box, tint)
		output:fill(subtitle, "#FFFFFF")
	end
end

function parallelogram(width, height, tilt)
	local p = path()

	p:move_to({ x = 0, y = 0 })
	p:line_to({ x = width, y = 0 })
	p:line_to({ x = width - tilt, y = height })
	p:line_to({ x = -tilt, y = height })
	p:close()

	return p
end

function size(base, limit, text)
	return math.floor(base * math.min(limit / text:len(), 1) + 0.5)
end

return title
