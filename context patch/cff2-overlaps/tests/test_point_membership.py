"""Independent audit of the monotonic-cubic fallback used only for validation."""
import importlib.util
import math
from pathlib import Path
import random
import unittest
from fontTools.pens.pointInsidePen import PointInsidePen

spec=importlib.util.spec_from_file_location('helper',Path(__file__).parents[1]/'font-cff-overlaps.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

DOME=[[0,0,'m'],[0,100,100,100,100,0,'c'],[100,-10,'l'],[0,-10,'l']]
REVERSE=[[0,0,'m'],[0,-10,'l'],[100,-10,'l'],[100,0,'l'],[100,100,0,100,0,0,'c']]

def transform(s,sx,sy,dx=0,dy=0):
    return [[*(v*(sx if i%2==0 else sy)+(dx if i%2==0 else dy) for i,v in enumerate(q[:-1])),q[-1]] for q in s]


def fonttools_inside(segments,point,evenodd=False):
    # Test-only independent oracle; FontTools is deliberately absent from the
    # runtime helper and explicitly blocked in test_no_fonttools.py.
    pen=PointInsidePen(None,point,evenOdd=evenodd);opened=False
    for segment in segments:
        tag=segment[-1];points=list(zip(segment[:-1:2],segment[1:-1:2]))
        if tag=='m':
            if opened:pen.closePath()
            pen.moveTo(points[0]);opened=True
        elif tag=='l':pen.lineTo(points[0])
        else:pen.curveTo(*points)
    if opened:pen.closePath()
    return pen.getResult()


class PointMembershipTests(unittest.TestCase):
    def check(self,segments,point,expected):
        self.assertEqual(h.robust_point_inside(segments,point),expected)
        self.assertEqual(h.robust_point_inside(segments,point,True),expected)
        winding=h.CompiledWinding(segments)(point)
        self.assertEqual(h.point_winding(segments,point),winding)
        self.assertEqual(bool(winding),expected)
        self.assertEqual(bool(winding%2),expected)
    def test_horizontal_tangency_and_shared_join_half_open(self):
        split=[[0,0,'m'],[0,50,25,75,50,75,'c'],[75,75,100,50,100,0,'c'],[100,-10,'l'],[0,-10,'l']]
        for shape in (DOME,split):
            for point,inside in [((-1,75),False),((50,74.9),True),((50,75.1),False),((50,0),True),((50,-9),True),((-1,0),False),((101,0),False)]:
                with self.subTest(point=point,shape=shape):self.check(shape,point,inside)
    def test_lower_tangency(self):
        shape=transform(DOME,1,-1)
        self.check(shape,(-1,-75),False);self.check(shape,(50,-74.9),True)
    def test_stationary_inflection(self):
        shape=[[0,-1,'m'],[10,1,20,-1,30,1,'c'],[30,-2,'l'],[0,-2,'l']]
        self.check(shape,(10,0),False);self.check(shape,(20,0),True)
    def test_orientation_and_winding_parity(self):
        for shape in (DOME,REVERSE):self.check(shape,(50,50),True)
        self.assertTrue(h.robust_point_inside(DOME+DOME,(50,50)))
        self.assertFalse(h.robust_point_inside(DOME+DOME,(50,50),True))
        self.check(DOME+REVERSE,(50,50),False)
    def test_multiple_subpath_closures(self):
        right=transform(DOME,1,1,200,0)
        for point,inside in [((50,20),True),((250,20),True),((150,20),False)]:self.check(DOME+right,point,inside)
    def test_affine_scales_and_near_flat_curve(self):
        for sx,sy,dx,dy in ((1e-6,1e-6,0,0),(1e6,1e6,0,0),(1,1e-8,0,0),(1,1,1e7,-1e7)):
            shape=transform(DOME,sx,sy,dx,dy)
            for point,inside in [((50,50),True),((-1,75),False),((50,76),False)]:
                self.check(shape,(point[0]*sx+dx,point[1]*sy+dy),inside)
    def test_original_fonttools_near_extremum_misclassification(self):
        shape=[[0,0,'m'],[0,100,100,100,100,0,'c'],[100,-100,0,-100,0,0,'c'],[50,0,'m'],[50,100,150,100,150,0,'c'],[150,-100,50,-100,50,0,'c']]
        converted=h.path_to_segments(h.pathops.simplify(h.segments_to_path(shape),fix_winding=True,keep_starting_points=True,clockwise=False))
        self.assertTrue(h.robust_point_inside(shape,(50,74.875)))
        self.check(converted,(50,74.875),True)
    def test_tiny_triangle_counter_validation_rejects_deleted_hole(self):
        outer=[[0,0,'m'],[1000,0,'l'],[1000,1000,'l'],[0,1000,'l']]
        original=outer+[[100,100,'m'],[100,100.1,'l'],[100.1,100,'l']]
        reference,tolerance=h.validation_reference(original,h.segments_to_path(original))
        self.assertIsNotNone(h.validate_result(original,outer,reference,tolerance))
        self.check(original,(100.01,100.01),False)
    def test_random_cubics_match_separate_ray_solver_away_from_edges(self):
        rng=random.Random(73493)
        for i in range(50):
            points=[(rng.uniform(-500,500),rng.uniform(-500,500)) for _ in range(4)]
            shape=[[*points[0],'m'],[*(v for p in points[1:] for v in p),'c']]
            for j in range(30):
                point=(rng.uniform(-600,600),rng.uniform(-600,600))
                # Separate FontTools cubic root solver provides independent
                # checking at ordinary random points (not extrema regressions).
                for evenodd in (False,True):
                    robust=h.robust_point_inside(shape,point,evenodd)
                    self.assertEqual(robust,fonttools_inside(shape,point,evenodd),(i,j,points,point))
                    self.assertEqual(h.point_inside(shape,point,evenodd),robust,(i,j,points,point))
                    winding=h.CompiledWinding(shape)(point)
                    self.assertEqual(bool(winding%2) if evenodd else bool(winding),robust,(i,j,points,point))

if __name__=='__main__':unittest.main()
