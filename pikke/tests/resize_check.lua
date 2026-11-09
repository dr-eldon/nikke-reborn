-- The live resize check's probe: load one image, resize it per the
-- flags, yield it (resize_check.py diffs the PNG against the
-- reference's own arithmetic). Path relative to this script.
arguments = {"path", "rw", "rh", "mode", "filter"}

function render(args)
  local img = image(args.path)
  local opts = {}
  -- Flag values are strings; the arithmetic coercion is the
  -- stdlib-less conversion.
  if args.rw then opts.width = args.rw + 0 end
  if args.rh then opts.height = args.rh + 0 end
  if args.mode then opts.mode = args.mode end
  if args.filter then opts.filter = args.filter end
  img:resize(opts)
  yield(img)
end
