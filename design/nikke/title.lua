local module = {}

local aire_exterior = font("../../fonts/AireExterior.ttf")
local chocolate = font("../../fonts/ChocolateClassicalSans-Regular.ttf")

function module.render(output, args)
	local title = text(args.title:upper(), {
		font = aire_exterior,
		size = module.size(150, 7, args.title),
		weight = 700,
		x = 50,
		y = math.floor(args.y),
	})

	local arrow = text("↖", {
		font = chocolate,
		size = module.size(50, 15, args.title),
		x = title.x + title.width,
		y = title.y + title.height,
	})
	arrow:translate({ x = 25, y = -arrow.height })

	local title_bounds = title.bounds:padded({ 20, 45 + arrow.width })
	local title_box = path()
	title_box:move_to({ x = title_bounds.x, y = title_bounds.y })
	title_box:line_to({
		x = title_bounds.x + title_bounds.width - title_bounds.height / 3,
		y = title_bounds.y,
	})
	title_box:line_to({
		x = title_bounds.x + title_bounds.width,
		y = title_bounds.y + title_bounds.height / 3,
	})
	title_box:line_to({
		x = title_bounds.x + title_bounds.width,
		y = title_bounds.y + title_bounds.height,
	})
	title_box:line_to({
		x = title_bounds.x,
		y = title_bounds.y + title_bounds.height,
	})
	title_box:close()

	local foreground = color("#FFFFFF")
	local background = color("#222222")

	if args.inverted then
		foreground, background = background, foreground
	end

	output:fill(title_box, background)
	output:fill(title, foreground)
	output:fill(arrow, foreground)

	local bar_width = math.min(math.max(title_bounds.width - 150, 80), 200)

	local bar = parallelogram(bar_width, 25, 25)
	bar:translate({ x = -40, y = title_bounds.y - 35 })

	local square = 25
	local spacing = square / 2
	local square_1 = parallelogram(square, 25, 25)
	square_1:translate({
		x = -40 + bar_width + spacing,
		y = title_bounds.y - 35,
	})

	local square_2 = parallelogram(square, 25, 25)
	square_2:translate({
		x = -40 + bar_width + square + 2 * spacing,
		y = title_bounds.y - 35,
	})

	local square_3 = parallelogram(square, 25, 25)
	square_3:translate({
		x = -40 + bar_width + 2 * square + 3 * spacing,
		y = title_bounds.y - 35,
	})

	output:fill(bar, background)
	output:fill(square_1, background)
	output:fill(square_2, background)
	output:fill(square_3, background)

	if args.subtitle ~= nil then
		local subtitle = text(args.subtitle:upper(), {
			font = aire_exterior,
			size = module.size(50, 15, args.subtitle),
			weight = 700,
			x = 50,
			y = title_bounds.y + title_bounds.height + spacing,
		})

		local subtitle_bounds = subtitle.bounds:padded({
			top = spacing,
			bottom = spacing,
			left = 50,
			right = 50,
		})
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
			x = subtitle_bounds.x
				+ subtitle_bounds.width
				- subtitle_bounds.height / 3,
			y = subtitle_bounds.y + subtitle_bounds.height,
		})
		subtitle_box:line_to({
			x = subtitle_bounds.x,
			y = subtitle_bounds.y + subtitle_bounds.height,
		})
		subtitle_box:close()

		local color = "#FFFFFF"
		local tint = args.tint:clone()

		if tint.c > 0.02 then
			tint.c = math.max(tint.c, 0.2)
		end

		if tint.l > 0.8 then
			color = "#222222"
			tint.l = math.min(tint.l, 0.9)
		else
			tint.l = math.min(tint.l, 0.7)
		end

		output:fill(subtitle_box, tint)
		output:fill(subtitle, color)
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

function module.size(base, limit, text)
	return math.floor(base * math.min(limit / text:len(), 1) + 0.5)
end

return module
