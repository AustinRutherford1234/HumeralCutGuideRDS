"""This file acts as the main module for this script."""

import traceback
import adsk.core
import adsk.fusion
import traceback
# import adsk.cam

# Initialize the global variables for the Application and UserInterface objects.
app = adsk.core.Application.get()
ui  = app.userInterface
handlers = []

def run(_context: str):
    """This function is called by Fusion when the script is run."""
    ui = None
    try:
        # Your code goes here.
        app = adsk.core.Application.get()
        ui  = app.userInterface

        # Create command definition
        cmdId = 'createSquareCmd'
        existingCmd = ui.commandDefinitions.itemById(cmdId)
        if existingCmd:
            existingCmd.deleteMe()
        cmdDef = ui.commandDefinitions.addButtonDefinition(cmdId, 'Create Square', 'Creates a user-defined square.')
        # Add command created event
        onCommandCreated = CommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)

        # Execute the command
        cmdDef.execute()

        # Keep the script running
        adsk.autoTerminate(False)

        # ui.messageBox(f'"{app.activeDocument.name}" is the active Document.')
    except:  #pylint:disable=bare-except
        # Write the error message to the TEXT COMMANDS window.

        app.log(f'Failed:\n{traceback.format_exc()}')
class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        cmd = args.command
        inputs = cmd.commandInputs

        # Add width and height inputs
        inputs.addValueInput('width', 'Width', 'mm', adsk.core.ValueInput.createByString('10'))
        inputs.addValueInput('length', 'Length', 'mm', adsk.core.ValueInput.createByString('10'))
        inputs.addValueInput('height', 'Height', 'mm', adsk.core.ValueInput.createByString('10'))
        inputs.addValueInput('holeDiameter', 'Hole Diameter', 'mm', adsk.core.ValueInput.createByString('5'))

        # Add execute handler
        onExecute = CommandExecuteHandler()
        cmd.execute.add(onExecute)
        handlers.append(onExecute)


# Event handler for the execute event
class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            ui  = app.userInterface
            design = adsk.fusion.Design.cast(app.activeProduct)
            rootComp = design.rootComponent

            # Get command inputs
            cmd = args.firingEvent.sender
            inputs = cmd.commandInputs
            width = inputs.itemById('width').value
            length = inputs.itemById('length').value
            height = inputs.itemById('height').value
            # Create sketch
            sketches = rootComp.sketches
            xyPlane = rootComp.xYConstructionPlane
            sketch = sketches.add(xyPlane)
            lines = sketch.sketchCurves.sketchLines
            # Create 4 points based on width and height
            p0 = adsk.core.Point3D.create(0, 0, 0)
            p1 = adsk.core.Point3D.create(width, 0, 0)
            p2 = adsk.core.Point3D.create(width, length, 0)
            p3 = adsk.core.Point3D.create(0, length, 0)
            p4 = adsk.core.Point3D.create(width/2, length/2, 0)
            # Draw lines
            line1 = lines.addByTwoPoints(p0, p1)
            line2 = lines.addByTwoPoints(p1, p2)
            line3 = lines.addByTwoPoints(p2, p3)
            line4 = lines.addByTwoPoints(p3, p0)
            radius = min(width, length) / 4  # adjust size as needed
            circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(p4, 1)
            # Add geometric constraints
            constraints = sketch.geometricConstraints
            constraints.addPerpendicular(line2, line3)
            constraints.addPerpendicular(line4, line1)
            constraints.addPerpendicular(line1, line2)
            constraints.addVertical(line2)
            constraints.addCoincident(line1.endSketchPoint, line2.startSketchPoint)
            constraints.addCoincident(line2.endSketchPoint, line3.startSketchPoint)
            constraints.addCoincident(line3.endSketchPoint, line4.startSketchPoint)
            constraints.addCoincident(line4.endSketchPoint, line1.startSketchPoint)
            originSketchPoint = sketch.originPoint
            constraints.addCoincident(line1.startSketchPoint, originSketchPoint)
            hole_input = inputs.itemById('holeDiameter')
            if hole_input:
                hole_diameter = hole_input.value
            else:
                ui.messageBox("Hole diameter input not found.")
                return
            dimensions = sketch.sketchDimensions
            dim_diameter = dimensions.addDiameterDimension(
                circle,
                adsk.core.Point3D.create(p4.x + 2, p4.y, 0)
            )
            hole_diameter = inputs.itemById('holeDiameter').value
            dim_diameter.parameter.value = hole_diameter
            dimensions.addDistanceDimension(
            line1.startSketchPoint, 
            line1.endSketchPoint, 
            adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
            adsk.core.Point3D.create(width / 2, -1, 0)
            )
            circleCenter = circle.centerSketchPoint
            dimensions.addDistanceDimension(
            line1.startSketchPoint,
            circleCenter,
            adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
            adsk.core.Point3D.create(width / 2, -1, 0)
            )
            dimensions.addDistanceDimension(
            line2.startSketchPoint,
            circleCenter,
            adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
            adsk.core.Point3D.create(width / 2, -1, 0)
            )
            dimensions.addDistanceDimension(
            line2.startSketchPoint, 
            line2.endSketchPoint, 
            adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
            adsk.core.Point3D.create(width + 1, length / 2, 0)
            )

            selectedProfile = None
            for i, profile in enumerate(sketch.profiles):
                outerLoops = 0
                innerLoops = 0
                for loop in profile.profileLoops:
                    if loop.isOuter:
                        outerLoops += 1
                    else:
                        innerLoops += 1
                if outerLoops == 1 and innerLoops >= 1:
                    selectedProfile = profile
                    break

            if not selectedProfile:
                ui.messageBox("No suitable profile with a hole was found.")
                return
            extrudes1 = rootComp.features.extrudeFeatures
            try:
                extInput1 = extrudes1.createInput(selectedProfile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            except:
                ui.messageBox('Failed creating input:\n{}'.format(traceback.format_exc()))
                return
             # Set the extrude input
            distance0 = adsk.core.ValueInput.createByString(f"{height*10} mm")
            extInput1.setDistanceExtent(False, distance0)
            extInput1.isSolid = True

            # Create the extrude
            extrude0 = extrudes1.add(extInput1)

            # Get the end face of the created extrude
            endFaceOfExtrude0 = extrude0.endFaces.item(0)

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
