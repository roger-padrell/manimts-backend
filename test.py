from manim import *

class MainScene(Scene):
    def construct(self):
        # Create a circle
        circle = Circle()
        
        # Create a square
        square = Square()
        
        # Create a triangle
        triangle = Triangle()
        
        # Set initial positions
        shapes = VGroup(circle, square, triangle).arrange(RIGHT, buff=1)
        
        # Add the shapes to the scene
        self.play(Create(shapes))
        
        # Animate the shapes
        self.play(
            circle.animate.set_fill(RED, opacity=0.5),
            square.animate.set_fill(BLUE, opacity=0.5),
            triangle.animate.set_fill(GREEN, opacity=0.5)
        )
        
        # Rotate the shapes
        self.play(
            Rotate(circle, angle=2*PI),
            Rotate(square, angle=2*PI),
            Rotate(triangle, angle=2*PI),
            run_time=2
        )
        
        # Scale the shapes
        self.play(
            circle.animate.scale(1.5),
            square.animate.scale(0.5),
            triangle.animate.scale(2)
        )
        
        # Wait before ending
        self.wait()