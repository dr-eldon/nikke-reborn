-- config = require(...) # We can require constants and other things here in the future; it's just Lua code!

function render(id, title, subtitle, animation, time)
  background = image("../../assets/images/backgrounds/sky-night.png")
  mask =  image("../../assets/images/designs/Card_Mask_Standard.png")
  logo_white = image("../../assets/images/Logo_White.png")
  logo_black = image("../../assets/images/Logo_Black.png")
  oswald = font("../../fonts/Oswald.ttf")
  aire_exterior = font("../../fonts/AireExterior.ttf")

  background = background.resize({width=width(), height=height(), mode="cover"})
  mask = mask.resize({width=width(), height=height()})
  logo_white = logo_white.resize({width=200})
  logo_black = logo_black.resize({width=200})

  base = background:contrast({ auto=true }):blend(mask)

  viewer_args = {
    "--width", physical_width(),
    "--height", physical_height(),
    "--half-body",
    "--stdout",
    id,
  }

  if animation ~= nil then
    viewer_args[#viewer_args + 1] = "--animation"
    viewer_args[#viewer_args + 1] = animation
  end

  if time ~= nil then
    viewer_args[#viewer_args + 1] = "--time"
    viewer_args[#viewer_args + 1] = time
  end

  character = spawn("nikke-viewer", viewer_args)

  -- We leverage iterators to execute the loop while the
  -- engine receives one frame at a time
  for frame in character do
    output = base:blend(frame)

    logo = rectangle({x = width() - 50 - logo_white:width(), y = 50, size = logo_white:size()})

    if output:luma_at(logo) > 127 then
      output = output:blend(logo_black, { at=logo, color_space="srgb" })
    else
      output = output:blend(logo_white, { at=logo, color_space="srgb" })
    end

    copyright = text("©PROXIMA BETA PTE. LTD. ©SHIFT UP CORP.",
      { font = oswald, size = 20, weight = 300, x = 50, y = height() - 50 })

    if output:luma_at(copyright:bounds()) > 127 then
      output = output:fill(copyright, "#000000")
    else
      output = output:fill(copyright, "#FFFFFF")
    end

    title = text(title,
      { font = aire_exterior, size = 150, weight = 700, x = 50, y = height() * 0.72 })

    -- TODO: Corner cutting
    output = output:fill(title:bounds():padded(30), "#333333")

    -- TODO: Subtitle...
    yield(output)
  end
end
