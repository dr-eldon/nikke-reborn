local module = {}

local oswald = font("../../fonts/Oswald.ttf")
local copyright = text("©PROXIMA BETA PTE. LTD. ©SHIFT UP CORP.", {
	font = oswald,
	size = 20,
	weight = 300,
})
local invert = nil

function module.render(output, position)
	copyright:move_to({ x = position.x, y = position.y - copyright.height })

	if invert == nil then
		invert = output:dominant_in(copyright.bounds):to_oklch().l > 0.5
	end

	if invert then
		output:fill(copyright, "#000000")
	else
		output:fill(copyright, "#FFFFFF")
	end
end

function module.reset()
	invert = nil
end

return module
