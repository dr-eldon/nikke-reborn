/// The viewport: the logical dims at the run's scale.
#[derive(Clone, Copy, Debug)]
pub struct Viewport {
    pub width: u32,
    pub height: u32,
    pub scale: f32,
}

impl Viewport {
    /// Logical → physical; the rounding ties away from zero.
    pub fn physical(&self, logical: f32) -> u32 {
        (logical * self.scale).round() as u32
    }

    pub fn physical_width(&self) -> u32 {
        self.physical(self.width as f32)
    }

    pub fn physical_height(&self) -> u32 {
        self.physical(self.height as f32)
    }
}

#[cfg(test)]
mod tests {
    use super::Viewport;

    // Exact against the reference's scaled values: the viewport and
    // the script's logo, copyright, and title.
    #[test]
    fn the_transform_is_exact_at_the_reference_values() {
        let viewport = Viewport {
            width: 1640,
            height: 2048,
            scale: 0.5,
        };
        assert_eq!(
            (viewport.physical_width(), viewport.physical_height()),
            (820, 1024)
        );
        assert_eq!(viewport.physical(200.0), 100);
        assert_eq!(viewport.physical(20.0), 10);
        assert_eq!(viewport.physical(150.0), 75);
    }
}
