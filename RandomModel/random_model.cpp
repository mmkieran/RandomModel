// Playing.cpp : Defines the entry point for the console application.

#include "stdafx.h"
#include <iostream>
#include <random>
#include <chrono>
#include <vector>
#include <stdio.h>
#include <time.h>


struct Point {
    int x;
    int y;
    int z;
};

struct Seed {

    std::default_random_engine randomGenerator;

    std::normal_distribution<double> normDist;
    std::uniform_real_distribution<double> expandChance;

    Point startLoc;
    double value;

    int blocksCoded;
    int blocksChecked;
    int maxBlocks;
};

struct Block {
    bool checked = false;
    bool coded = false;
    double value;
};

struct Model {
    Block* blocks;
    int xSize, ySize, zSize;
    int xLowerBound, yLowerBound, zLowerBound;
    int xUpperBound, yUpperBound, zUpperBound;
    Seed seed;
};

Model* createModel(int xSize, int ySize, int zSize) {
    Model* model = (Model*)malloc(sizeof(Model));
    model->blocks = (Block*)malloc(sizeof(Block) * xSize * ySize * zSize);
    memset(model->blocks, 0, sizeof(Block) * xSize * ySize * zSize);

    model->xSize = xSize;
    model->ySize = ySize;
    model->zSize = zSize;

    model->xLowerBound = int(xSize * 0.1);
    model->yLowerBound = int(ySize * 0.1);
    model->zLowerBound = int(zSize * 0.1);

    model->xUpperBound = int(xSize * 0.9);
    model->yUpperBound = int(ySize * 0.9);
    model->zUpperBound = int(zSize * 0.9);

    //Since we just get a block of memory, we need to initialize values or we start checking junk
    //for (int i = 0; i < xSize * ySize * zSize; i++) {
    //    model->blocks[i].checked = false;
    //    model->blocks[i].coded = false;
    //    model->blocks[i].value = -1;
    //}

    return model;
};

void destroyModel(Model* model) {
    free(model->blocks);
    free(model);
}

int getBlockIndex(Model* model, int x, int y, int z) {
    //We are using a 1-D array, so we need to calculate distance along the array from 3D points
    return (z * model->xSize * model->ySize + x * model->ySize + y);
};

Block* getBlock(Model* model, Point* p) {
    Block* out = nullptr;
    out = &model->blocks[getBlockIndex(model, p->x, p->y, p->z)];
    return out;
};

void generateModelSeed(Model* model, unsigned seed, double average, double stdev, int maxBlocks) {

    //Pass in time and return struct with appropriate data
    std::default_random_engine generator(seed);
    model->seed.randomGenerator = generator;

    //generate normal distribution value for seed using average and standard deviation
    std::normal_distribution<double> normal(average, stdev);
    model->seed.normDist = normal;

    //Generate uniform distribution for expansion chance from 0 to 1
    std::uniform_real_distribution<double> uniform(0.0, 1.0);
    model->seed.expandChance = uniform;

    //Pick a random starting location
    srand(time(NULL));
    model->seed.startLoc.x = rand() % model->xUpperBound + model->xLowerBound;
    model->seed.startLoc.y = rand() % model->yUpperBound + model->yLowerBound;
    model->seed.startLoc.z = rand() % model->zUpperBound + model->zLowerBound;

    //Code the seed value to the starting location
    model->seed.value = model->seed.normDist(model->seed.randomGenerator);
    Block* block = getBlock(model, &model->seed.startLoc);
    block->value = model->seed.value;

    block->checked = true;
    block->coded = true;
    model->seed.blocksCoded = 1;
    model->seed.blocksChecked = 1;

    model->seed.maxBlocks = maxBlocks;

};

bool checkModelBounds(Model* model, Point* p) {
    if (p->x >= model->xLowerBound && p->x < model->xUpperBound) {
        if (p->y >= model->yLowerBound && p->y < model->yUpperBound) {
            if (p->z >= model->zLowerBound && p->z < model->zUpperBound) {
                return true;
            }
        }
    }
    return false;
};

std::vector<Point> codeNeighborhood(Model* model, Point block, double* codeChance, int preferentialDirection) {
    //Take coded block and check/code neighbors, add passing blocks to list, and return to be processed
    std::vector<Point> blocksToProcess;
    for (int dx = -1; dx < 2; dx++) {
        for (int dy = -1; dy < 2; dy++) {
            for (int dz = -1; dz < 2; dz++) {
                if (model->seed.blocksCoded >= model->seed.maxBlocks) {
                    blocksToProcess.clear();
                    return blocksToProcess;
                }
                if (dx == 0 && dy == 0 && dz == 0) { continue; }

                Point neighborLoc = { block.x + dx, block.y + dy, block.z + dz };
                if (!checkModelBounds(model, &neighborLoc)) {
                    model->seed.blocksChecked++;
                    continue;
                }

                double adjustedChance = 0;
                if (dx != 0 && preferentialDirection == 1) { adjustedChance = 0.1; }
                else if (dy != 0 && preferentialDirection == 2) { adjustedChance = 0.1; }
                else if (dz != 0 && preferentialDirection == 3) { adjustedChance = 0.1; }

                Block* neighbor = getBlock(model, &neighborLoc);
                if (neighbor->checked == false && model->seed.expandChance(model->seed.randomGenerator) <= (*codeChance + adjustedChance) ) {
                    neighbor->value = model->seed.normDist(model->seed.randomGenerator);
                    neighbor->checked = true;
                    neighbor->coded = true;
                    blocksToProcess.push_back(neighborLoc);
                    model->seed.blocksCoded++;
                    model->seed.blocksChecked++;
                }
                else {
                    *codeChance = *codeChance * ( (model->seed.maxBlocks - model->seed.blocksCoded) / model->seed.maxBlocks);
                    neighbor->checked = true;
                    model->seed.blocksChecked++;
                }
            }
        }
    }
    return blocksToProcess;
};

void processBlocks(Model* model, std::vector<Point> blockList, double codeChance) {
    //Loop through list of blocks, code them, and process newly coded blocks
    int preferentialDirection = rand() % 3 + 1; //1 = dx, 2=dy, 3=dz
    while (blockList.size() >= 1) {
        std::vector<Point> newBlockList;
        for (auto&& block : blockList) {
            std::vector<Point> tmp;
            tmp = codeNeighborhood(model, block, &codeChance, preferentialDirection);
            if (tmp.size() > 0) {
                newBlockList.insert(newBlockList.end(), tmp.begin(), tmp.end());
            }
        }
        blockList = newBlockList;
    }
};

void printModel(Model * model) {
    //Output to stdout by bench for debugging... Don't use with large data sets!
    for (int z = 0; z < model->zSize; z++) {
        for (int y = 0; y < model->ySize; y++) {
            for (int x = 0; x < model->xSize; x++) {
                Point p = { x, y, z };
                fprintf(stdout, "%f, ", getBlock(model, &p)->value);
            }
            fprintf(stdout, "\n");
        }
        fprintf(stdout, "\n");
    }
};

void writeReportFile(Model* model) {
    FILE* reportFile;
    int err = fopen_s(&reportFile, "model_report.txt", "w");
    if (err == 0) {
        fprintf(reportFile, "Seed location: %d, %d, %d\n", model->seed.startLoc.x+1, model->seed.startLoc.y+1, model->seed.startLoc.z+1);
        fprintf(reportFile, "Seed value: %f\n", model->seed.value);
        fprintf(reportFile, "Blocks checked: %d\n", model->seed.blocksChecked);
        fprintf(reportFile, "Blocks coded: %d\n", model->seed.blocksCoded);
    }
    fclose(reportFile);
};

void writeModelFile(Model* model, bool writeMissingVals=false) {
    FILE* modelFile;
    double missingValue = -1;
    int err = fopen_s(&modelFile, "model.csv", "w");
    if (err == 0) {
        fprintf(modelFile, "X,Y,Z,Value,\n"); //Write the header
        for (int z = 0; z < model->zSize; z++) {
            for (int y = 0; y < model->ySize; y++) {
                for (int x = 0; x < model->xSize; x++) {
                    Point p = { x, y, z };
                    Block* block = getBlock(model, &p);
                    if (block->coded) {
                        fprintf(modelFile, "%d,%d,%d,%f,\n", x+1, y+1, z+1, block->value);
                    }
                    else if (writeMissingVals) {
                        fprintf(modelFile, "%d,%d,%d,%f,\n", x+1, y+1, z+1, missingValue);
                    }
                }
            }
        }
    }
    fclose(modelFile);
};

int main(int argc, char* argv[]) {

    //start clock timer
    typedef std::chrono::high_resolution_clock myclock;
    myclock::time_point beginning = myclock::now();

    //Check and parse command-line arguments
    int nx, ny, nz, maxblocks;
    double avg, stdev;

    if (argc != 13) {
        fprintf(stdout, "\nUsage: -nx [int] -ny [int] -nz [int] -avg [double] -stdev [double] -maxblocks [int]\n");
        fprintf(stdout, "\nExample: RandomModel.exe -nx 2 -ny 3 -nz 4 -avg 3.0 -stdev 0.25 -maxblocks 5\n");
        fprintf(stdout, "\nPress any key...\n");
        std::cin.get();
        exit(0);
    }
    else {
        for (int i = 1; i < argc; i++) {
            if (strcmp(argv[i], "-nx") == 0) {
                nx = atoi(argv[i + 1]);
            }
            else if (strcmp(argv[i], "-ny") == 0) {
                ny = atoi(argv[i + 1]);
            }
            else if (strcmp(argv[i], "-nz") == 0) {
                nz = atoi(argv[i + 1]);
            }
            else if (strcmp(argv[i], "-avg") == 0) {
                avg = atof(argv[i + 1]);
            }
            else if (strcmp(argv[i], "-stdev") == 0) {
                stdev = atof(argv[i + 1]);
            }
            else if (strcmp(argv[i], "-maxblocks") == 0) {
                maxblocks = atoi(argv[i + 1]);
            }
        }
    }

    //Create a blank model
    Model* model = createModel(nx, ny, nz);

    //Select random number seed from clock time difference
    myclock::duration d = myclock::now() - beginning;
    unsigned seed = d.count();

    //Pick the seed location and setup random number generators
    generateModelSeed(model, seed, avg, stdev, maxblocks);

    //Process the starting seed location
    std::vector<Point> start = { model->seed.startLoc };
    processBlocks(model, start, 1); //ADD COMMAND LINE OPTION for code chance?

    //Write or print model for debugging
    //printModel(model);
    writeModelFile(model, false);

    //Write Seed information to report file
    writeReportFile(model);

    //Destroy the model and free memory
    destroyModel(model);

    return 0;
}

