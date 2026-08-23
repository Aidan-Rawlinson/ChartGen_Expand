# template

## Yellow box resolution

Each detected yellow box resolves against the slide's placeholders into one of three outcomes, checked in this order.

1. **Fully contained.** Use the placeholder's position and size. Remove both the box and the placeholder from the cleaned template.
2. **No overlap with any placeholder.** Free-floating. Use the box's own position and size, carried as its own entry named after its PowerPoint shape name. Remove only the box.
3. **Partial overlap, short of containment.** Ambiguous. Leave it entirely alone: not classified, not added to the Running Order, not removed from the cleaned template. Raise a warning.

Containment allows 1mm (36,000 EMU) of drift per edge, which absorbs the sub-visible rounding seen on copy-pasted shapes.

A box whose text matches no content type is stripped and warned, never silently dropped.

## Fill colour

A shape can carry colour two ways: an explicit fill, or a Shape Styles `fillRef` that stores no colour at all. Detection resolves both.

Order: explicit fill on the shape; then, only if the shape defines no fill whatsoever, its style's `fillRef`. An explicit `<a:noFill/>` means no fill, full stop, and the style reference is not consulted.

A `schemeClr` name is not looked up directly. It passes through the colour map in effect for that slide, the slide's own `clrMapOvr` if present and otherwise the master's `clrMap`, and only the redirected name is looked up in the theme's `clrScheme`. Master-level context is cached per master.

Theme `fillStyleLst` shaded and gradient variants are not modelled. The base scheme colour is used unmodified.
