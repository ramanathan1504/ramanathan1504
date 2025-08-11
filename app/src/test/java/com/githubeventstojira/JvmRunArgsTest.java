package com.githubeventstojira;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class JvmRunArgsTest {
    private static final Logger logger = LogManager.getLogger(JvmRunArgsTest.class);

    public static void main(String[] args) {
        logger.info("Testing JVM runtime args lookup");
    }
}